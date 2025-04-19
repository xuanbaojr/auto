from service.attendant_check import AttendantCheck
import logging, queue, threading, os
import subprocess, av, time
from concurrent.futures import ThreadPoolExecutor
import cv2
import datetime

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
    def __init__(self, rtsp_url_1, rtsp_url_2, rtsp_url_3, rtsp_url_4, output_dir, buffer_size=30, 
                analysis_workers=2, segment_length=300, reconnect_attempts=5, analyze_frame=None):
        
        self.workers = []
        self.rtsp_url_1 = rtsp_url_1
        self.rtsp_url_2 = rtsp_url_2
        self.rtsp_url_3 = rtsp_url_3
        self.rtsp_url_4 = rtsp_url_4
        self.output_dir = output_dir
        self.buffer_size = buffer_size
        self.analysis_workers = analysis_workers
        self.segment_length = segment_length
        self.reconnect_attempts = reconnect_attempts
        self.stop_signal = threading.Event()  # Initialize stop_signal
        self.cap_1 = Camera(rtsp_url_1)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('RTSPProcessor')

        self.should_record = False
        self.is_recording = False
        self.last_segment_time = 0
        self.recording_proc_1, self.recording_proc_2, self.recording_proc_3, self.recording_proc_4 = None, None, None, None
        self.analyze_frame = analyze_frame

        os.makedirs(output_dir, exist_ok=True)
                
    def start(self):
        self.logger.info("Starting RTSP processor...")
        
        while not self.stop_signal.is_set():
            try:
                frame = self.cap_1.getFrame()
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
            now = datetime.datetime.now()
            date_folder = now.strftime("%d_%m_%Y")

            hour = now.strftime("%H")
            minute = now.strftime("%M")
            second = now.strftime("%S")

            nested_path_init = os.path.join(self.output_dir, date_folder, hour, minute, second)
            os.makedirs(nested_path_init, exist_ok=True)
            
            # Store initial output path (without duration)
            self.initial_output_path_cam1 = os.path.join(nested_path_init, "cam1.mp4")
            self.initial_output_path_cam2 = os.path.join(nested_path_init, "cam2.mp4")
            self.initial_output_path_cam3 = os.path.join(nested_path_init, "cam3.mp4")
            self.initial_output_path_cam4 = os.path.join(nested_path_init, "cam4.mp4")
            
            self.recording_cmd_1 = [
                'ffmpeg',
                '-y',
                '-rtsp_transport', 'tcp',
                '-rtsp_flags', 'prefer_tcp',
                '-stimeout', '5000000',
                '-i', self.rtsp_url_1,
                '-c:v', 'libx265',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                self.initial_output_path_cam1  # Using the stored path
            ]

            self.recording_cmd_2 = [
                'ffmpeg',
                '-y',
                '-rtsp_transport', 'tcp',
                '-rtsp_flags', 'prefer_tcp',
                '-stimeout', '5000000',
                '-i', self.rtsp_url_2,
                '-c:v', 'libx265',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                self.initial_output_path_cam2  # Using the stored path
            ]

            self.recording_cmd_3 = [
                'ffmpeg',
                '-y',
                '-rtsp_transport', 'tcp',
                '-rtsp_flags', 'prefer_tcp',
                '-stimeout', '5000000',
                '-i', self.rtsp_url_3,
                '-c:v', 'libx265',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                self.initial_output_path_cam3  # Using the stored path
            ]

            self.recording_cmd_4 = [
                'ffmpeg',
                '-y',
                '-rtsp_transport', 'tcp',
                '-rtsp_flags', 'prefer_tcp',
                '-stimeout', '5000000',
                '-i', self.rtsp_url_4,
                '-c:v', 'libx265',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                self.initial_output_path_cam4  # Using the stored path
            ]
            
            # Start recording process with optimized configuration
            self.recording_proc_1 = subprocess.Popen(
                self.recording_cmd_1,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0,
            )

            self.recording_proc_2 = subprocess.Popen(
                self.recording_cmd_2,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0,
            )

            self.recording_proc_3 = subprocess.Popen(
                self.recording_cmd_3,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0,
            )

            self.recording_proc_4 = subprocess.Popen(
                self.recording_cmd_4,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
            
            
            # Update recording state
            self.is_recording = True
            self.last_segment_time = time.time()
            self.recording_start_time = time.time()
            self.logger.info(f"Started recording to .mp4 file with H.265 encoding")
            
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            self.is_recording = False
            for proc_name in ['recording_proc_1', 'recording_proc_2', 'recording_proc_3', 'recording_proc_4']:
                if hasattr(self, proc_name) and getattr(self, proc_name):
                    try:
                        getattr(self, proc_name).kill()
                    except:
                        pass
                    setattr(self, proc_name, None)

    def _stop_recording(self):
        """Stop all camera recordings and organize files with duration information"""
        # Check if we're actually recording
        recording_procs = [
            self.recording_proc_1, self.recording_proc_2, 
            self.recording_proc_3, self.recording_proc_4
        ]
        
        if not any(recording_procs):
            self.is_recording = False
            self.logger.info("No recording processes to stop")
            return
                
        try:
            # Calculate recording duration
            recording_duration = time.time() - self.recording_start_time
            duration_seconds = int(round(recording_duration))
            
            # Process all recording processes
            for i, proc in enumerate([self.recording_proc_1, self.recording_proc_2, 
                                    self.recording_proc_3, self.recording_proc_4], 1):
                if proc is None:
                    continue
                    
                # Send 'q' to FFmpeg stdin for graceful termination
                if proc.stdin:
                    try:
                        proc.stdin.write(b'q')
                        proc.stdin.flush()
                    except (BrokenPipeError, IOError) as e:
                        self.logger.warning(f"Could not write to FFmpeg stdin for cam{i}: {e}")
                
                # Wait for process to finish with timeout
                timeout = 15 if recording_duration < 20 else 10
                try:
                    proc.wait(timeout=timeout)
                    self.logger.info(f"Recording stopped for cam{i} after {recording_duration:.2f} seconds")
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"FFmpeg process for cam{i} did not terminate gracefully, forcing termination")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.logger.error(f"FFmpeg termination failed for cam{i}, killing process")
                        proc.kill()
            
            # Get the base directory where videos are stored (date/hour/minute)
            if hasattr(self, 'initial_output_path_cam1'):
                base_dir = os.path.dirname(os.path.dirname(self.initial_output_path_cam1))  # Go up two levels (from date/hour/minute/second)
                current_dir_name = os.path.basename(os.path.dirname(self.initial_output_path_cam1))  # Get the "second" part
                
                # Create new directory with duration: second_duration
                new_dir_name = f"{current_dir_name}_{duration_seconds}"
                new_dir_path = os.path.join(base_dir, new_dir_name)
                
                # Create the new directory
                os.makedirs(new_dir_path, exist_ok=True)
                
                # Move all camera files to the new directory
                for cam_num in range(1, 5):
                    src_path = getattr(self, f"initial_output_path_cam{cam_num}", None)
                    if src_path and os.path.exists(src_path):
                        dst_filename = f"cam{cam_num}.mp4"
                        dst_path = os.path.join(new_dir_path, dst_filename)
                        
                        try:
                            os.rename(src_path, dst_path)
                            self.logger.info(f"Moved cam{cam_num} video to: {dst_path}")
                        except Exception as e:
                            self.logger.error(f"Failed to move cam{cam_num} video: {e}")
                
                # Remove the original second directory if it's empty
                try:
                    original_dir = os.path.dirname(self.initial_output_path_cam1)
                    if os.path.exists(original_dir) and not os.listdir(original_dir):
                        os.rmdir(original_dir)
                except Exception as e:
                    self.logger.warning(f"Could not remove original directory: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error in _stop_recording: {e}")
        finally:
            # Clean up all recording processes
            self.recording_proc_1 = None
            self.recording_proc_2 = None
            self.recording_proc_3 = None
            self.recording_proc_4 = None
            self.is_recording = False
            self.logger.info(f"All recordings stopped after {recording_duration:.2f} seconds")

    
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
    attendant_check = AttendantCheck()  
    from dotenv import load_dotenv
    import os

    load_dotenv()  # Load environment variables from .env file

    rtsp_url1 = os.getenv('RTSP_URL1')
    rtsp_url2 = os.getenv('RTSP_URL2')
    rtsp_url3 = os.getenv('RTSP_URL3')
    rtsp_url4 = os.getenv('RTSP_URL4')
    output_dir = "./output_video"
    try:
        processor = RTSPProcessor(
            rtsp_url_1=rtsp_url1,
            rtsp_url_2=rtsp_url2,
            rtsp_url_3=rtsp_url3,
            rtsp_url_4=rtsp_url4,
            output_dir=output_dir,
            buffer_size=60,
            analysis_workers=2,
            segment_length=50,  # 5-minute segments
            reconnect_attempts=5,
            analyze_frame=attendant_check.is_attendant_in_booth
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