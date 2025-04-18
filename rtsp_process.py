from service.booth_check import BoothCheck
import logging, queue, threading, os
import subprocess, av, time
from concurrent.futures import ThreadPoolExecutor



class RTSPProcessor:
    def __init__(self, rtsp_url, output_dir, buffer_size=30, 
                analysis_workers=2, segment_length=300, reconnect_attempts=5, analyze_frame=None):
                
        self.rtsp_url = rtsp_url
        self.output_dir = output_dir
        self.buffer_size = buffer_size
        self.analysis_workers = analysis_workers
        self.segment_length = segment_length
        self.reconnect_attempts = reconnect_attempts

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('RTSPProcessor')

        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.packet_queue = queue.Queue(maxsize=buffer_size)
        self.should_record = False
        self.is_recording = False
        self.stop_signal = threading.Event()
        self.last_segment_time = 0
        self.recording_proc = None

        self.ffmpeg_cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',           # More reliable than UDP
            '-rtsp_flags', 'prefer_tcp',        # Force TCP when possible
            '-stimeout', '5000000',             # 5 second timeout
            '-i', self.rtsp_url,
            '-c', 'copy',                       # Passthrough without re-encoding
            '-f', 'matroska',                   # Matroska container format
            'pipe:1'                            # Output to stdout
        ]

        self.proc = None
        self.container = None
        self.analyze_frame = analyze_frame

        os.makedirs(output_dir, exist_ok=True)
        # self.camera_render = CameraRender(rtsp_url=rtsp_url, logger=self.logger, stop_signal=self.stop_signal)

    
    def start(self):
        self.logger.info("Starting RTSP processor...")
        self.stop_signal.clear()
        self._start_ffmpeg()
        self.workers = []

        packet_reader = threading.Thread(target=self._packet_reader_thread)
        packet_reader.daemon = True
        packet_reader.start()
        self.workers.append(packet_reader)

        frame_decoder = threading.Thread(target=self._frame_decoder_thread)
        frame_decoder.daemon = True
        frame_decoder.start()
        self.workers.append(frame_decoder)

        self.analyzer_pool = ThreadPoolExecutor(max_workers=self.analysis_workers)

        packet_writer = threading.Thread(target=self._packet_writer_thread)
        packet_writer.daemon = True
        packet_writer.start()
        self.workers.append(packet_writer)

        # viewer_thread = threading.Thread(target=self.camera_render._viewer_thread)
        # viewer_thread.daemon = True
        # viewer_thread.start()
        # self.workers.append(viewer_thread)

        self.logger.info("RTSP processor started")
        return self
                
    
    def _start_ffmpeg(self):
        self.logger.info("Starting FFmpeg subprocess...")
        self.proc = subprocess.Popen(
            self.ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )

        try:
            self.container = av.open(self.proc.stdout, format='matroska')
            self.logger.info("FFmpeg subprocess started successfully")
        except Exception as e:
            self.logger.error(f"Failed to open container: {e}")
            self._cleanup()
            raise
    
    def _cleanup(self, keep_running=False):
        if self.container:
            try:
                self.container.close()
            except:
                pass
            self.container = None
        
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except:
                try:
                    self.proc.kill()
                except:
                    pass
            self.proc = None

        if self.is_recording:
            self._stop_recording()
            
        # Also stop the viewer
        # self.camera_render._stop_viewer()

        if not keep_running:
            self.stop_signal.set()
    
    def _stop_recording(self):
        """Stop the current recording and finalize MP4 file"""
        if not hasattr(self, 'recording_proc') or not self.recording_proc:
            self.is_recording = False
            return
            
        try:
            # Calculate recording duration
            recording_duration = time.time() - self.recording_start_time
            
            # For very short recordings, add a small delay to ensure proper finalization
            # if recording_duration < 20:
            #     self.logger.info(f"Short recording detected ({recording_duration:.2f}s), ensuring proper finalization")
            #     time.sleep(1)  # Give FFmpeg a moment to process buffered frames
                
            # Send 'q' to FFmpeg stdin for graceful termination
            if self.recording_proc.stdin:
                try:
                    self.recording_proc.stdin.write(b'q')
                    self.recording_proc.stdin.flush()
                except (BrokenPipeError, IOError) as e:
                    self.logger.warning(f"Could not write to FFmpeg stdin: {e}")
            
            # Wait for process to finish with a generous timeout
            # Longer timeout for short recordings to ensure proper finalization
            timeout = 15 if recording_duration < 20 else 10
            try:
                self.recording_proc.wait(timeout=timeout)
                self.logger.info(f"Recording stopped after {recording_duration:.2f} seconds")
            except subprocess.TimeoutExpired:
                self.logger.warning("FFmpeg process did not terminate gracefully, forcing termination")
                self.recording_proc.terminate()
                try:
                    self.recording_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.error("FFmpeg termination failed, killing process")
                    self.recording_proc.kill()
                    
            # Verify the output file exists and has content
            if hasattr(self, 'recording_cmd'):
                output_path = self.recording_cmd[-1]
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    if file_size < 1024:  # Less than 1KB is suspicious
                        self.logger.warning(f"Output file seems too small ({file_size} bytes), may be corrupted")
                else:
                    self.logger.error(f"Output file {output_path} was not created")
                    
        except Exception as e:
            self.logger.error(f"Error stopping recording: {e}")
            try:
                self.recording_proc.kill()
            except:
                pass
        finally:
            self.recording_proc = None
            self.is_recording = False

    def _packet_reader_thread(self):
        self.logger.info("Packet reader thread started")

        try:
            for packet in self.container.demux(video=0):
                if self.stop_signal.is_set():
                    break

                if packet.dts is None:
                    continue

                if not self.packet_queue.full():
                    self.packet_queue.put(packet, block=False)
        except Exception as e:
            self.logger.error(f"Error in packet reader: {e}")
            self._attempt_reconnect()
        
        self.logger.info("Packet reader thread stopped")

    def _frame_decoder_thread(self):
        self.logger.info("Frame decoder thread started")
        try:
            while not self.stop_signal.is_set():
                if self.packet_queue.qsize() > 0:
                    packet = self.packet_queue.get()
                    for frame in packet.decode():
                        img = frame.to_ndarray(format="bgr24")
                        if not self.frame_queue.full():
                            result = self.analyze_frame(img)
                            if result and not self.should_record:
                                self.should_record = True
                                self.logger.info("Analysis indicates recording should start")
                            elif not result and self.should_record:
                                self.should_record = False
                                self.logger.info("Analysis indicates recording should stop")

        except Exception as e:
            self.logger.error(f"Error in frame decoder: {e}")
        
        self.logger.info("Frame decoder thread stopped")

    
    def _start_recording(self):
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            output_path = os.path.join(self.output_dir, f"capture_{timestamp}.mp4")
            
            # Create a second FFmpeg instance directly connecting to the RTSP stream
            self.recording_cmd = [
                'ffmpeg',
                '-y',
                '-rtsp_transport', 'tcp',           # More reliable than UDP
                '-rtsp_flags', 'prefer_tcp',        # Force TCP when possible
                '-stimeout', '5000000',             # 5 second timeout
                '-i', self.rtsp_url,                # Use the original RTSP URL directly
                '-c:v', 'libx265',                  # Use H.264 instead of H.265 for faster encoding
                '-preset', 'ultrafast',             # Faster encoding preset for short clips
                '-crf', '23',                       # Constant Rate Factor (quality level, lower = better)
                '-pix_fmt', 'yuv420p',              # Standard pixel format for compatibility
                '-movflags', '+faststart',          # Optimize for web streaming
                output_path
            ]
            
            # Start recording process with pipe for graceful termination
            self.recording_proc = subprocess.Popen(
                self.recording_cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_recording = True
            self.last_segment_time = time.time()
            self.recording_start_time = time.time()  # Track when recording started
            self.logger.info(f"Started recording to {output_path} with H.264 encoding")
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            self.is_recording = False
            self.recording_proc = None

    def _packet_writer_thread(self):
        self.logger.info("Packet writer thread started")
        min_recording_duration = 5  # Minimum recording duration in seconds

        while not self.stop_signal.is_set():
            try:
                current_time = time.time()
                
                # Handle recording state changes
                if self.should_record and not self.is_recording:
                    self._start_recording()
                elif not self.should_record and self.is_recording:
                    # Check if minimum recording duration has been met
                    recording_duration = current_time - self.recording_start_time
                    if recording_duration < min_recording_duration:
                        wait_time = min_recording_duration - recording_duration
                        self.logger.info(f"Enforcing minimum recording duration, waiting {wait_time:.2f}s before stopping")
                        time.sleep(wait_time)
                    
                    self._stop_recording()
                    self.logger.info("Recording stopped")

                # Handle segment rotation
                if self.is_recording:
                    # Check if we need to start a new segment
                    if (current_time - self.last_segment_time) > self.segment_length:
                        self.logger.info("Rotating recording segment")
                        self._stop_recording()
                        self._start_recording()
                        self.logger.info("New recording segment started")
                    
                    # Check if the recording process is still running
                    if hasattr(self, 'recording_proc') and self.recording_proc:
                        if self.recording_proc.poll() is not None:
                            # Process has exited
                            exit_code = self.recording_proc.poll()
                            stderr_output = self.recording_proc.stderr.read().decode('utf-8', errors='ignore')
                            
                            if exit_code != 0:
                                self.logger.error(f"FFmpeg recording process exited with code {exit_code}")
                                self.logger.error(f"FFmpeg stderr output: {stderr_output}")
                            else:
                                self.logger.info("FFmpeg recording process completed successfully")
                                
                            self.is_recording = False
                            self.recording_proc = None
                            
                            if self.should_record:
                                self._start_recording()
                
                time.sleep(0.5)  # Reduced polling frequency
                
            except Exception as e:
                self.logger.error(f"Error in packet writer: {e}")
                if self.is_recording:
                    self._stop_recording()  # Try to clean up recording if error occurs
                time.sleep(1)  # Wait a bit before retrying after an error

        self.logger.info("Packet writer thread stopped")

    def _attempt_reconnect(self):
        self.logger.info("Attempting to reconnect to RTSP stream...")
        self._cleanup(keep_running=True)
        for attempt in range(1, self.reconnect_attempts + 1):
            self.logger.info(f"Reconnection attempt {attempt}/{self.reconnect_attempts}")
            delay = 2 ** attempt
            time.sleep(delay)
            try:
                self._start_ffmpeg()
                self.logger.info("Reconnection successful")
                return True
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt} failed: {e}")
        self.logger.error("All reconnection attempts failed")
        return False
    
    def stop(self):
        """Stop the RTSP processor and clean up resources"""
        self.logger.info("Stopping RTSP processor...")
        
        # Signal all threads to stop
        self.stop_signal.set()
        
        # Clean up resources
        self._cleanup()
        
        # Wait for threads to complete
        for thread in self.workers:
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        # Shutdown thread pool
        if hasattr(self, 'analyzer_pool'):
            self.analyzer_pool.shutdown(wait=False)
        
        self.logger.info("RTSP processor stopped")

class CameraRender:
    def __init__(self, rtsp_url, logger, stop_signal):
        self.rtsp_url = rtsp_url
        self.stop_signal = stop_signal
        self.logger = logger
        self.ffplay_cmd = [
            'ffplay',
            '-rtsp_transport', 'tcp',
            '-fflags', 'nobuffer',
            '-flags', 'low_delay',
            '-framedrop',
            # REMOVE '-infbuf', to prevent unlimited buffering
            '-sync', 'ext',       # Add external clock synchronization
            '-vf', "drawtext=text='%{frame_num}':x=20:y=20:fontsize=48:fontcolor=yellow:box=1:boxcolor=black@0.5:boxborderw=5",
            self.rtsp_url
        ]
        self.viewer_proc = None  # Process for the ffplay viewer
    
    def _viewer_thread(self):
        """Thread function that runs and manages the ffplay process"""
        self.logger.info("Starting ffplay viewer with frame counter...")
        
        # Keep trying to restart the viewer if it crashes, until stop_signal is set
        while not self.stop_signal.is_set():
            try:
                # Start ffplay process with frame counter
                self.viewer_proc = subprocess.Popen(
                    self.ffplay_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,  # No input needed
                    bufsize=10**8
                )
                
                self.logger.info("ffplay viewer started with frame counter")
                
                # Wait for the process to end or for stop_signal
                while not self.stop_signal.is_set():
                    # Check if process is still running
                    if self.viewer_proc.poll() is not None:
                        exit_code = self.viewer_proc.poll()
                        stderr_output = self.viewer_proc.stderr.read().decode('utf-8', errors='ignore')
                        self.logger.error(f"ffplay viewer exited with code {exit_code}: {stderr_output}")
                        break
                    
                    # Sleep to reduce CPU usage
                    time.sleep(1)
                
                # Clean up the viewer process
                self._stop_viewer()
                
                # If we're exiting because of stop_signal, don't restart
                if self.stop_signal.is_set():
                    break
                    
                # Otherwise, wait before restarting
                self.logger.info("Restarting viewer in 3 seconds...")
                time.sleep(3)
                
            except Exception as e:
                self.logger.error(f"Error in viewer thread: {e}")
                # Clean up in case of exception
                self._stop_viewer()
                # Wait before retry
                time.sleep(3)
        
        self.logger.info("Viewer thread stopped")
    
    def _stop_viewer(self):
        """Stop the ffplay viewer process"""
        if hasattr(self, 'viewer_proc') and self.viewer_proc:
            try:
                # Check if process is still running
                if self.viewer_proc.poll() is None:
                    # Try graceful termination first
                    self.viewer_proc.terminate()
                    try:
                        self.viewer_proc.wait(timeout=5)
                        self.logger.info("Viewer process terminated gracefully")
                    except subprocess.TimeoutExpired:
                        self.logger.warning("Viewer process not responding to termination, forcing kill")
                        self.viewer_proc.kill()
                        self.viewer_proc.wait(timeout=2)
            except Exception as e:
                self.logger.error(f"Error stopping viewer process: {e}")
                try:
                    self.viewer_proc.kill()
                except:
                    pass
            finally:
                self.viewer_proc = None

        
def main():
    booth_check = BoothCheck()

    from dotenv import load_dotenv
    import os

    load_dotenv()  # Load environment variables from .env file

    rtsp_url1 = os.getenv('RTSP_URL1')
    output_dir = "./videos"
    os.makedirs(output_dir, exist_ok=True)
    try:
        processor = RTSPProcessor(
            rtsp_url=rtsp_url1,
            output_dir=output_dir,
            buffer_size=60,
            analysis_workers=2,
            segment_length=20,  # 5-minute segments
            reconnect_attempts=5,
            analyze_frame=booth_check.check
        )
      
        processor.start()
        print("Processing RTSP stream... Press Ctrl+C to stop")
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