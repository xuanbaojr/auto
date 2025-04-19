from service.booth_check import BoothCheck
import logging, queue, threading, os
import subprocess, av, time
from concurrent.futures import ThreadPoolExecutor
import cv2

import threading
from threading import Lock
import cv2

class Camera:
    last_frame = None
    last_ready = None
    lock = Lock()

    def __init__(self, rtsp_link):
        capture = cv2.VideoCapture(rtsp_link)
        thread = threading.Thread(target=self.rtsp_cam_buffer, args=(capture,), name="rtsp_read_thread")
        thread.daemon = True
        thread.start()

    def rtsp_cam_buffer(self, capture):
        while True:
            with self.lock:
                self.last_ready, self.last_frame = capture.read()


    def getFrame(self):
        if (self.last_ready is not None) and (self.last_frame is not None):
            return self.last_frame.copy()
        else:
            return None



class RTSPProcessor:
    def __init__(self, rtsp_url, output_dir, buffer_size=30, 
                analysis_workers=2, segment_length=300, reconnect_attempts=5, analyze_frame=None):
        
        self.workers = []
        self.rtsp_url = rtsp_url
        self.cap = Camera(rtsp_url)
        self.output_dir = output_dir
        self.buffer_size = buffer_size
        self.analysis_workers = analysis_workers
        self.segment_length = segment_length
        self.reconnect_attempts = reconnect_attempts
        self.stop_signal = threading.Event()  # Initialize stop_signal

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('RTSPProcessor')

        self.should_record = False
        self.is_recording = False
        self.last_segment_time = 0
        self.recording_proc = None
        self.analyze_frame = analyze_frame

        os.makedirs(output_dir, exist_ok=True)
                
    def start(self):
        self.logger.info("Starting RTSP processor...")
        
        while not self.stop_signal.is_set():
            try:
                frame = self.cap.getFrame()
                if frame is None:
                    time.sleep(0.01)  # Small sleep to prevent CPU spinning
                    continue
                
                # Run frame analysis
                result = self.analyze_frame(frame)
                
                # Start recording only when result is True and not already recording
                if result and not self.is_recording:
                    self._start_recording()
                    self.logger.info("Analysis indicates recording should start")
                # Stop recording when result becomes False and currently recording
                elif not result and self.is_recording:
                    self._stop_recording()
                    self.logger.info("Analysis indicates recording should stop")
                
                # Check if segment length exceeded and we need to start a new segment
                if self.is_recording and time.time() - self.last_segment_time > self.segment_length:
                    self.logger.info(f"Segment length {self.segment_length}s exceeded, starting new segment")
                    self._stop_recording()
                    # Only restart recording if result is still True
                    if result:
                        self._start_recording()
                
                time.sleep(0.01)  # Small sleep to prevent CPU spinning
                
            except Exception as e:
                self.logger.error(f"Error in main processing loop: {e}")
                time.sleep(0.1)  # Short wait before retrying
    
    def _start_recording(self):
        """Start a new recording immediately with optimized parameters"""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            output_path = os.path.join(self.output_dir, f"capture_{timestamp}.mp4")
            
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
            
            
            # Start recording process with optimized configuration
            self.recording_proc = subprocess.Popen(
                self.recording_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,  # Redirect stdout to prevent blocking
                stderr=subprocess.PIPE,
                bufsize=0,                  # Unbuffered operation for lower latency
            )
            
            # Update recording state
            self.is_recording = True
            self.last_segment_time = time.time()
            self.recording_start_time = time.time()
            self.logger.info(f"Started recording to {output_path} with H.264 encoding")
            
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            self.is_recording = False
            if hasattr(self, 'recording_proc') and self.recording_proc:
                try:
                    self.recording_proc.kill()  # Clean up if exception occurred
                except:
                    pass
            self.recording_proc = None
    
    def _stop_recording(self):
        """Stop the current recording and finalize MP4 file"""
        if not hasattr(self, 'recording_proc') or not self.recording_proc:
            self.is_recording = False
            print("No recording process to stop")
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

    
    def _cleanup(self):
        """Clean up resources"""
        if self.is_recording:
            self._stop_recording()
    
    def stop(self):
        """Stop the RTSP processor and clean up resources"""
        self.logger.info("Stopping RTSP processor...")
        self.stop_signal.set()
        self._cleanup()
        self.logger.info("RTSP processor stopped")
        
def main():
    booth_check = BoothCheck()

    from dotenv import load_dotenv
    import os

    load_dotenv()  # Load environment variables from .env file

    rtsp_url1 = os.getenv('RTSP_URL2')
    print("rtsp_url1", rtsp_url1)
    output_dir = "./videos"
    os.makedirs(output_dir, exist_ok=True)
    try:
        processor = RTSPProcessor(
            rtsp_url=rtsp_url1,
            output_dir=output_dir,
            buffer_size=60,
            analysis_workers=2,
            segment_length=50,  # 5-minute segments
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