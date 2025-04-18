import logging
import queue
import threading
import os
import subprocess
import time
import random
import av
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable, Optional, Any, Union, Tuple

class CameraStream:
    """
    Encapsulates a single camera stream with its processing logic.
    
    This class handles the connection to a single RTSP stream, frame extraction,
    analysis, and recording functionality.
    """
    
    def __init__(self, 
                 rtsp_url: str, 
                 camera_id: int, 
                 output_dir: str, 
                 stop_signal: threading.Event,
                 analyze_frame: Callable[[Any], bool] = None,
                 **kwargs):
        """
        Initialize a camera stream processor.
        
        Args:
            rtsp_url: The RTSP URL for this camera
            camera_id: Unique identifier for this camera
            output_dir: Directory where recordings will be saved
            stop_signal: Event to signal when processing should stop
            analyze_frame: Function to analyze video frames (takes numpy array, returns boolean)
            **kwargs: Additional configuration options
        """
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self.output_dir = output_dir
        self.stop_signal = stop_signal
        self.analyze_frame = analyze_frame
        
        # Configuration options with defaults
        self.buffer_size = kwargs.get('buffer_size', 30)
        self.reconnect_attempts = kwargs.get('reconnect_attempts', 5)
        self.ffmpeg_config = kwargs.get('ffmpeg_config', DEFAULT_FFMPEG_CONFIG)
        
        # Processing queues
        self.frame_queue = queue.Queue(maxsize=self.buffer_size)
        self.packet_queue = queue.Queue(maxsize=self.buffer_size)
        
        # State tracking
        self.should_record = False
        self.is_recording = False
        self.recording_proc = None
        self.last_segment_time = 0
        self.recording_start_time = 0
        
        # Stream handling
        self.proc = None
        self.container = None
        
        # Thread management
        self.threads = []
        
        # Configure logging
        self.logger = kwargs.get('logger', logging.getLogger(f'Camera-{camera_id}'))
        
        # Build FFmpeg command
        self.ffmpeg_cmd = [
            'ffmpeg',
            *self.ffmpeg_config['input_options'],
            '-i', self.rtsp_url,
            *self.ffmpeg_config['output_options']['stream'],
            'pipe:1'
        ]
    
    def start(self) -> 'CameraStream':
        """Start processing this camera stream."""
        self.logger.info(f"Starting camera {self.camera_id} stream processing...")
        
        try:
            self._start_ffmpeg()
            
            # Start processing threads
            packet_reader = threading.Thread(
                target=self._packet_reader_thread,
                name=f"cam{self.camera_id}-packet-reader"
            )
            packet_reader.daemon = True
            packet_reader.start()
            self.threads.append(packet_reader)
            
            frame_decoder = threading.Thread(
                target=self._frame_decoder_thread,
                name=f"cam{self.camera_id}-frame-decoder"
            )
            frame_decoder.daemon = True
            frame_decoder.start()
            self.threads.append(frame_decoder)
            
            self.logger.info(f"Camera {self.camera_id} stream processing started")
            return self
            
        except Exception as e:
            self.logger.error(f"Failed to start camera {self.camera_id}: {e}")
            self._cleanup()
            raise
    
    def _start_ffmpeg(self) -> None:
        """Start FFmpeg subprocess with robust error handling."""
        if self.proc is not None:
            self._cleanup_ffmpeg()
            
        self.logger.info(f"Starting FFmpeg for camera {self.camera_id}")
        
        self.proc = subprocess.Popen(
            self.ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
        
        try:
            # Add timeout to container open to prevent hanging
            self.container = av.open(self.proc.stdout, format='matroska', timeout=10000000)
            self.logger.info(f"FFmpeg subprocess for camera {self.camera_id} started successfully")
        except Exception as e:
            stderr_output = ""
            if self.proc and self.proc.stderr:
                stderr_output = self.proc.stderr.read().decode('utf-8', errors='ignore')
            
            self.logger.error(f"Failed to open container for camera {self.camera_id}: {e}")
            self.logger.error(f"FFmpeg stderr output: {stderr_output}")
            self._cleanup_ffmpeg()
            raise
    
    def _cleanup_ffmpeg(self) -> None:
        """Clean up FFmpeg resources."""
        if self.container:
            try:
                self.container.close()
            except Exception as e:
                self.logger.warning(f"Error closing container for camera {self.camera_id}: {e}")
            self.container = None
        
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception as e:
                    self.logger.warning(f"Failed to kill FFmpeg process for camera {self.camera_id}: {e}")
            self.proc = None
    
    def _cleanup(self) -> None:
        """Clean up all resources for this camera."""
        self._cleanup_ffmpeg()
        
        if self.is_recording:
            self._stop_recording()
    
    def _packet_reader_thread(self) -> None:
        """Thread to read packets from the RTSP stream."""
        self.logger.info(f"Packet reader thread for camera {self.camera_id} started")
        
        reconnect_attempt = 0
        max_empty_packets = 100  # Maximum number of consecutive empty packets before reconnect
        empty_packet_count = 0
        
        while not self.stop_signal.is_set():
            try:
                if not self.container:
                    if not self._attempt_reconnect():
                        # If reconnection failed, wait a bit before retrying
                        if self.stop_signal.wait(5):
                            break
                        continue
                
                packet_count = 0
                for packet in self.container.demux(video=0):
                    if self.stop_signal.is_set():
                        break
                    
                    if packet.dts is None:
                        empty_packet_count += 1
                        if empty_packet_count >= max_empty_packets:
                            self.logger.warning(f"Too many empty packets for camera {self.camera_id}, reconnecting...")
                            self._cleanup_ffmpeg()
                            break
                        continue
                    
                    empty_packet_count = 0  # Reset counter on valid packet
                    
                    try:
                        self.packet_queue.put(packet, block=True, timeout=1)
                        packet_count += 1
                        
                        # Periodically yield to avoid blocking for too long
                        if packet_count % 30 == 0:
                            time.sleep(0.01)
                    except queue.Full:
                        # Queue is full, skip this packet
                        continue
                
                # If we exit the loop without error but without processing packets,
                # there might be an issue with the stream
                if packet_count == 0 and not self.stop_signal.is_set():
                    self.logger.warning(f"No packets received for camera {self.camera_id}, reconnecting...")
                    reconnect_attempt += 1
                    self._cleanup_ffmpeg()
                    
                    # Add increasing delay between reconnection attempts
                    delay = min(30, 2 ** reconnect_attempt)
                    if self.stop_signal.wait(delay):
                        break
                    
                    self._start_ffmpeg()
                    reconnect_attempt = 0  # Reset counter on successful reconnect
            
            except Exception as e:
                self.logger.error(f"Error in packet reader for camera {self.camera_id}: {e}")
                reconnect_attempt += 1
                
                self._cleanup_ffmpeg()
                
                # Add increasing delay between reconnection attempts
                delay = min(30, 2 ** reconnect_attempt)
                if self.stop_signal.wait(delay):
                    break
                
                try:
                    self._start_ffmpeg()
                    reconnect_attempt = 0  # Reset counter on successful reconnect
                except Exception as e:
                    self.logger.error(f"Failed to reconnect camera {self.camera_id}: {e}")
                    # Continue to next iteration, which will try again with increased delay
        
        self.logger.info(f"Packet reader thread for camera {self.camera_id} stopped")
    
    def _frame_decoder_thread(self) -> None:
        """Thread to decode frames and run analysis."""
        self.logger.info(f"Frame decoder thread for camera {self.camera_id} started")
        
        analyzer_active = self.analyze_frame is not None
        skip_count = 0  # For frame skipping if needed
        
        try:
            while not self.stop_signal.is_set():
                try:
                    # Use a timeout to periodically check the stop signal
                    packet = self.packet_queue.get(block=True, timeout=1)
                except queue.Empty:
                    continue
                
                for frame in packet.decode():
                    if self.stop_signal.is_set():
                        break
                    
                    # Skip frames if needed for performance
                    skip_count = (skip_count + 1) % 2  # Process every other frame
                    if skip_count != 0:
                        continue
                    
                    if analyzer_active:
                        try:
                            img = frame.to_ndarray(format="bgr24")
                            result = self.analyze_frame(img)
                            
                            # Update recording state based on analysis
                            if result and not self.should_record:
                                self.should_record = True
                                self.logger.info(f"Camera {self.camera_id}: Analysis indicates recording should start")
                            elif not result and self.should_record:
                                self.should_record = False
                                self.logger.info(f"Camera {self.camera_id}: Analysis indicates recording should stop")
                        except Exception as e:
                            self.logger.error(f"Error in frame analysis for camera {self.camera_id}: {e}")
                
                # Signal that we're done with this packet
                self.packet_queue.task_done()
                
        except Exception as e:
            self.logger.error(f"Error in frame decoder for camera {self.camera_id}: {e}")
        
        self.logger.info(f"Frame decoder thread for camera {self.camera_id} stopped")
    
    def _attempt_reconnect(self) -> bool:
        """Attempt to reconnect to the RTSP stream with exponential backoff."""
        self.logger.info(f"Attempting to reconnect camera {self.camera_id}...")
        
        for attempt in range(1, self.reconnect_attempts + 1):
            # Calculate delay with exponential backoff and small jitter
            delay = min(30, (2 ** attempt) + random.uniform(0, 1))
            
            self.logger.info(f"Reconnection attempt {attempt}/{self.reconnect_attempts} "
                           f"for camera {self.camera_id} (waiting {delay:.2f}s)")
            
            # Wait for delay but also check stop signal
            if self.stop_signal.wait(delay):
                self.logger.info(f"Reconnection for camera {self.camera_id} cancelled due to stop signal")
                return False
            
            try:
                self._start_ffmpeg()
                self.logger.info(f"Reconnection for camera {self.camera_id} successful")
                return True
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt} for camera {self.camera_id} failed: {e}")
        
        self.logger.error(f"All reconnection attempts for camera {self.camera_id} failed")
        return False
    
    def start_recording(self, timestamp=None) -> bool:
        """
        Start recording this camera's stream to a file.
        
        Args:
            timestamp: Optional timestamp string for the filename (for synchronized recordings)
        
        Returns:
            bool: True if recording started successfully, False otherwise
        """
        if self.is_recording:
            self.logger.warning(f"Camera {self.camera_id} is already recording")
            return True
            
        try:
            if timestamp is None:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                
            output_path = os.path.join(
                self.output_dir, 
                f"capture_{timestamp}_cam{self.camera_id}.mp4"
            )
            
            recording_cmd = [
                'ffmpeg',
                '-y',
                *self.ffmpeg_config['input_options'],
                '-i', self.rtsp_url,
                *self.ffmpeg_config['output_options']['record'],
                output_path
            ]
            
            # Start recording process with pipe for graceful termination
            self.recording_proc = subprocess.Popen(
                recording_cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_recording = True
            self.last_segment_time = time.time()
            self.recording_start_time = time.time()
            self.logger.info(f"Started recording camera {self.camera_id} to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start recording camera {self.camera_id}: {e}")
            self.is_recording = False
            self.recording_proc = None
            return False
    
    def stop_recording(self) -> bool:
        """
        Stop the current recording and finalize MP4 file.
        
        Returns:
            bool: True if recording stopped successfully, False otherwise
        """
        if not self.is_recording or not self.recording_proc:
            self.is_recording = False
            self.recording_proc = None
            return True
            
        try:
            # Calculate recording duration
            recording_duration = time.time() - self.recording_start_time
            
            if self.recording_proc.stdin:
                try:
                    self.recording_proc.stdin.write(b'q')
                    self.recording_proc.stdin.flush()
                except (BrokenPipeError, IOError) as e:
                    self.logger.warning(f"Could not write to FFmpeg stdin for camera {self.camera_id}: {e}")
            
            # Wait for process to finish with a generous timeout
            # Longer timeout for short recordings to ensure proper finalization
            timeout = 15 if recording_duration < 20 else 10
            try:
                self.recording_proc.wait(timeout=timeout)
                self.logger.info(f"Recording stopped for camera {self.camera_id} after {recording_duration:.2f} seconds")
            except subprocess.TimeoutExpired:
                self.logger.warning(f"FFmpeg recording process for camera {self.camera_id} did not terminate gracefully, forcing termination")
                self.recording_proc.terminate()
                try:
                    self.recording_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.error(f"FFmpeg termination failed for camera {self.camera_id}, killing process")
                    self.recording_proc.kill()
            
            # Verify the output file exists and has content
            if hasattr(self, 'recording_cmd'):
                output_path = self.recording_cmd[-1]
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    if file_size < 1024:  # Less than 1KB is suspicious
                        self.logger.warning(f"Output file for camera {self.camera_id} seems too small ({file_size} bytes), may be corrupted")
                else:
                    self.logger.error(f"Output file {output_path} for camera {self.camera_id} was not created")
            
            return True
                
        except Exception as e:
            self.logger.error(f"Error stopping recording for camera {self.camera_id}: {e}")
            try:
                if self.recording_proc:
                    self.recording_proc.kill()
            except Exception:
                pass
            
            return False
            
        finally:
            self.recording_proc = None
            self.is_recording = False


# Default FFmpeg configuration that can be overridden
DEFAULT_FFMPEG_CONFIG = {
    'input_options': [
        '-rtsp_transport', 'tcp',
        '-rtsp_flags', 'prefer_tcp',
        '-stimeout', '5000000',
    ],
    'output_options': {
        'stream': [
            '-c', 'copy',
            '-f', 'matroska'
        ],
        'record': [
            '-c:v', 'libx265',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart'
        ]
    }
}


class RTSPProcessor:
    """
    Main class for processing multiple RTSP streams with synchronized recording.
    
    This class manages multiple CameraStream instances, handling synchronized
    recording based on analysis results from a configurable camera.
    """
    
    def __init__(self, 
                 rtsp_urls: List[str], 
                 output_dir: str, 
                 analyze_frame: Callable[[Any], bool] = None,
                 **kwargs):
        """
        Initialize the RTSP processor.
        
        Args:
            rtsp_urls: List of RTSP URLs for cameras (can contain None for unused slots)
            output_dir: Directory where recordings will be saved
            analyze_frame: Function to analyze video frames (takes numpy array, returns boolean)
            **kwargs: Additional configuration options
        """
        # Setup logging
        logging.basicConfig(
            level=kwargs.get('log_level', logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('RTSPProcessor')
        
        # Basic parameters
        self.output_dir = output_dir
        self.analyze_frame = analyze_frame
        
        # Configuration with defaults
        self.buffer_size = kwargs.get('buffer_size', 30)
        self.segment_length = kwargs.get('segment_length', 300)  # 5 minutes by default
        self.reconnect_attempts = kwargs.get('reconnect_attempts', 5)
        self.min_recording_duration = kwargs.get('min_recording_duration', 5)  # seconds
        
        # Calculate optimal thread count based on CPU availability
        cpu_count = os.cpu_count() or 4
        camera_count = len([url for url in rtsp_urls if url])
        self.analysis_workers = kwargs.get('analysis_workers', 
                                          max(1, min(cpu_count - 1, camera_count)))
        
        # State variables
        self.should_record = False
        self.is_recording = False
        self.stop_signal = threading.Event()
        self.recording_lock = threading.RLock()
        self.last_segment_time = 0
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize cameras
        self.cameras = []
        for idx, url in enumerate(rtsp_urls, 1):
            if url:  # Only create for non-empty URLs
                try:
                    camera = CameraStream(
                        rtsp_url=url,
                        camera_id=idx,
                        output_dir=output_dir,
                        stop_signal=self.stop_signal,
                        analyze_frame=analyze_frame if idx == 2 else None,  # Only camera 2 analyzes frames in this example
                        buffer_size=self.buffer_size,
                        reconnect_attempts=self.reconnect_attempts,
                        logger=logging.getLogger(f'Camera-{idx}'),
                        ffmpeg_config=kwargs.get('ffmpeg_config', DEFAULT_FFMPEG_CONFIG)
                    )
                    self.cameras.append(camera)
                except Exception as e:
                    self.logger.error(f"Failed to initialize camera {idx}: {e}")
        
        # Thread tracking
        self.workers = []
        self.analyzer_pool = None
    
    def start(self) -> 'RTSPProcessor':
        """Start the RTSP processor."""
        self.logger.info("Starting RTSP processor...")
        self.stop_signal.clear()
        
        try:
            # Start all camera streams
            for camera in self.cameras:
                try:
                    camera.start()
                except Exception as e:
                    self.logger.error(f"Failed to start camera {camera.camera_id}: {e}")
            
            # Create analysis thread pool
            self.analyzer_pool = ThreadPoolExecutor(max_workers=self.analysis_workers)
            
            # Start the recording manager thread
            recording_manager = threading.Thread(
                target=self._recording_manager_thread,
                name="recording-manager"
            )
            recording_manager.daemon = True
            recording_manager.start()
            self.workers.append(recording_manager)
            
            self.logger.info(f"RTSP processor started with {len(self.cameras)} cameras")
            return self
            
        except Exception as e:
            self.logger.error(f"Failed to start RTSP processor: {e}")
            self.stop()
            raise
    
    def _recording_manager_thread(self) -> None:
        """Thread that manages recording state across all cameras."""
        self.logger.info("Recording manager thread started")
        
        while not self.stop_signal.is_set():
            try:
                current_time = time.time()
                
                # Aggregate recording state from analysis camera (camera 2)
                any_should_record = any(camera.should_record for camera in self.cameras if camera.camera_id == 2)
                
                # Handle recording state changes
                if any_should_record and not self.is_recording:
                    self._start_recording()
                elif not any_should_record and self.is_recording:
                    # Check if minimum recording duration has been met
                    recording_duration = current_time - self.last_segment_time
                    if recording_duration < self.min_recording_duration:
                        wait_time = self.min_recording_duration - recording_duration
                        self.logger.info(f"Enforcing minimum recording duration, waiting {wait_time:.2f}s before stopping")
                        if self.stop_signal.wait(wait_time):
                            break
                    
                    self._stop_recording()
                
                # Handle segment rotation
                if self.is_recording:
                    # Check if we need to start a new segment
                    if (current_time - self.last_segment_time) > self.segment_length:
                        self.logger.info("Rotating recording segment")
                        self._stop_recording()
                        self._start_recording()
                
                # Shorter sleep interval for more responsive recording
                if self.stop_signal.wait(0.5):
                    break
                
            except Exception as e:
                self.logger.error(f"Error in recording manager: {e}")
                if self.is_recording:
                    self._stop_recording()  # Try to clean up recording if error occurs
                
                # Longer sleep after an error
                if self.stop_signal.wait(1):
                    break
        
        self.logger.info("Recording manager thread stopped")
    
    def _start_recording(self) -> None:
        """Start synchronized recording across all cameras."""
        with self.recording_lock:
            if self.is_recording:
                return
                
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.logger.info(f"Starting synchronized recording with timestamp {timestamp}")
            
            # Start recording on all cameras with the same timestamp
            successful = True
            for camera in self.cameras:
                if not camera.start_recording(timestamp):
                    successful = False
            
            if successful:
                self.is_recording = True
                self.last_segment_time = time.time()
                self.logger.info("Synchronized recording started successfully")
            else:
                self.logger.error("Failed to start recording on some cameras")
                # Try to stop any recordings that did start
                for camera in self.cameras:
                    if camera.is_recording:
                        camera.stop_recording()
    
    def _stop_recording(self) -> None:
        """Stop recording on all cameras."""
        with self.recording_lock:
            if not self.is_recording:
                return
                
            self.logger.info("Stopping all recordings")
            
            # Stop recording on all cameras
            for camera in self.cameras:
                camera.stop_recording()
            
            self.is_recording = False
            self.logger.info("All recordings stopped")
    
    def stop(self) -> None:
        """Stop the RTSP processor and clean up resources."""
        self.logger.info("Stopping RTSP processor...")
        
        # Signal all threads to stop
        self.stop_signal.set()
        
        # Stop recording if active
        if self.is_recording:
            self._stop_recording()
        
        # Stop all cameras
        for camera in self.cameras:
            try:
                camera._cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up camera {camera.camera_id}: {e}")
        
        # Wait for worker threads to complete
        for thread in self.workers:
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        # Shutdown thread pool
        if self.analyzer_pool:
            self.analyzer_pool.shutdown(wait=False)
        
        self.logger.info("RTSP processor stopped")


def main():
    """Main entry point for the application."""
    from service.attendant_check import AttendantCheck
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    rtsp_urls = [
        os.getenv('RTSP_URL1'),
        os.getenv('RTSP_URL2'),
        os.getenv('RTSP_URL3'),
        os.getenv('RTSP_URL4')
    ]
    
    output_dir = "./videos"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize attendant check
    attendant_check = AttendantCheck()
    
    try:
        # Create and start processor
        processor = RTSPProcessor(
            rtsp_urls=rtsp_urls,
            output_dir=output_dir,
            buffer_size=60,
            analysis_workers=2,
            segment_length=20,  # 20-second segments for testing
            reconnect_attempts=5,
            min_recording_duration=5,  # At least 5 seconds of recording
            analyze_frame=attendant_check.is_attendant_in_booth
        )
        
        processor.start()
        print("Processing RTSP streams... Press Ctrl+C to stop")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        if 'processor' in locals():
            processor.stop()
            print("Processor stopped")


if __name__ == "__main__":
    main()