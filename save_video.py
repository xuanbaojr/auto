import cv2
import numpy as np
import threading
from threading import Lock
import time
import os
import logging
import subprocess
import datetime
from dotenv import load_dotenv

class ThreadedCamera:
    """Single camera handler that reads frames in a separate thread to prevent UI blocking"""
    def __init__(self, rtsp_url, name="Camera"):
        self.rtsp_url = rtsp_url
        self.name = name
        self.last_frame = None
        self.last_ready = False
        self.lock = Lock()
        self.running = True
        
        # Start the reading thread
        self.thread = threading.Thread(target=self._rtsp_cam_buffer, name=f"rtsp_thread_{name}")
        self.thread.daemon = True
        self.thread.start()
    
    def _rtsp_cam_buffer(self):
        """Thread function that continuously reads frames from the camera"""
        cap = cv2.VideoCapture(self.rtsp_url)
        
        # Optimize buffer size and other settings for RTSP
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer to get the most recent frame
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('H', '2', '6', '4'))  # Use H264 if available
        
        reconnect_attempts = 0
        last_reconnect_time = 0
        
        while self.running:
            try:
                # Read a frame
                ret, frame = cap.read()
                
                # Update the last frame with the lock for thread safety
                with self.lock:
                    self.last_ready = ret
                    if ret:
                        self.last_frame = frame
                        reconnect_attempts = 0
                    else:
                        # Only try to reconnect if a certain time has passed since last attempt
                        current_time = time.time()
                        if current_time - last_reconnect_time > 3:  # Throttle reconnection attempts
                            print(f"Reconnecting to {self.name}...")
                            cap.release()
                            cap = cv2.VideoCapture(self.rtsp_url)
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('H', '2', '6', '4'))
                            last_reconnect_time = current_time
                            reconnect_attempts += 1
                
                # Small sleep to prevent thread from consuming 100% CPU
                time.sleep(0.01)
            
            except Exception as e:
                print(f"Error in camera thread {self.name}: {e}")
                with self.lock:
                    self.last_ready = False
                time.sleep(1)  # Sleep longer on error
        
        # Clean up resources when thread is stopping
        cap.release()
    
    def get_frame(self):
        """Thread-safe method to get the latest frame"""
        with self.lock:
            if self.last_ready and self.last_frame is not None:
                return True, self.last_frame.copy()
            else:
                return False, None
    
    def release(self):
        """Stop the camera thread and release resources"""
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)  # Wait for thread to finish


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
        self.cap_1 = ThreadedCamera(rtsp_url_1, "Camera 1")  # Using our ThreadedCamera implementation

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
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(target=self.start, name="rtsp_processor_thread")
        self.processing_thread.daemon = True
        self.processing_thread.start()
                
    def start(self):
        self.logger.info("Starting RTSP processor...")
        
        while not self.stop_signal.is_set():
            try:
                ret, frame = self.cap_1.get_frame()
                if not ret or frame is None:
                    time.sleep(0.01)  # Small sleep to prevent CPU spinning
                    continue
                
                # Run frame analysis
                result = self.analyze_frame(frame)
                time.sleep(0.05)  # Small sleep to prevent CPU spinning
                
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
            
            # FFmpeg commands for each camera
            self.recording_cmd_1 = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-i', self.rtsp_url_1,
                '-c', 'copy',
                self.initial_output_path_cam1
            ]
            
            self.recording_cmd_2 = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-i', self.rtsp_url_2,
                '-c', 'copy',
                self.initial_output_path_cam2
            ]
            
            self.recording_cmd_3 = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-i', self.rtsp_url_3,
                '-c', 'copy',
                self.initial_output_path_cam3
            ]
            
            self.recording_cmd_4 = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-i', self.rtsp_url_4,
                '-c', 'copy',
                self.initial_output_path_cam4
            ]
            
            # Start recording processes with optimized configuration
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
        
        # Wait for the processing thread to finish
        if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)
            
        self._cleanup()
        self.logger.info("RTSP processor stopped")


class CameraRenderWithRecordingStatus:
    """Display feeds from 4 cameras in a 2x2 grid with recording status on Camera 1"""
    def __init__(self, rtsp_processor):
        # Store reference to the RTSPProcessor
        self.rtsp_processor = rtsp_processor
        
        # Initialize camera objects with threading (reuse the same URLs as the processor)
        self.camera1 = self.rtsp_processor.cap_1  # Reuse the first camera from the processor
        self.camera2 = ThreadedCamera(rtsp_processor.rtsp_url_2, "Camera 2")
        self.camera3 = ThreadedCamera(rtsp_processor.rtsp_url_3, "Camera 3")
        self.camera4 = ThreadedCamera(rtsp_processor.rtsp_url_4, "Camera 4")
        
        # Performance tracking
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.fps = 0
    
    def show_video(self):
        """
        Display feeds from 4 cameras in a 2x2 grid layout.
        Show recording status on Camera 1 based on RTSPProcessor's is_recording state.
        """
        # Define the final display resolution
        display_width, display_height = 1280, 720
        
        # Calculate the size of each camera view
        cam_width = display_width // 2
        cam_height = display_height // 2
        
        # Target FPS to limit CPU usage
        target_fps = 30
        frame_time = 1.0 / target_fps
        
        try:
            while True:
                loop_start = time.time()
                
                # Create a blank canvas for the combined view
                combined_frame = np.zeros((display_height, display_width, 3), dtype=np.uint8)
                
                # Get frames from all cameras - non-blocking operations
                ret1, frame1 = self.camera1.get_frame()
                ret2, frame2 = self.camera2.get_frame()
                ret3, frame3 = self.camera3.get_frame()
                ret4, frame4 = self.camera4.get_frame()
                
                # Prepare fallback frame for missing cameras
                fallback_frame = np.zeros((cam_height, cam_width, 3), dtype=np.uint8)
                cv2.putText(fallback_frame, "Camera Unavailable", (10, cam_height//2), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Process each camera feed individually - only resize valid frames
                frame1_resized = cv2.resize(frame1, (cam_width, cam_height)) if ret1 else fallback_frame.copy()
                frame2_resized = cv2.resize(frame2, (cam_width, cam_height)) if ret2 else fallback_frame.copy()
                frame3_resized = cv2.resize(frame3, (cam_width, cam_height)) if ret3 else fallback_frame.copy() 
                frame4_resized = cv2.resize(frame4, (cam_width, cam_height)) if ret4 else fallback_frame.copy()
                
                # Add recording status to Camera 1 feed based on RTSPProcessor's is_recording
                if ret1:
                    is_recording = self.rtsp_processor.is_recording
                    status_text = "RECORDING: TRUE" if is_recording else "RECORDING: FALSE"
                    status_color = (0, 255, 0) if is_recording else (0, 0, 255)  # Green for true, red for false
                    cv2.putText(frame1_resized, status_text, (10, cam_height - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color, 2)
                    
                    # Print the recording status to console as required
                    result_print = "1" if is_recording else "00000000000000000000000000000000000"
                    print(result_print)
                
                # Place each camera in its quadrant
                combined_frame[0:cam_height, 0:cam_width] = frame1_resized
                combined_frame[0:cam_height, cam_width:display_width] = frame2_resized
                combined_frame[cam_height:display_height, 0:cam_width] = frame3_resized
                combined_frame[cam_height:display_height, cam_width:display_width] = frame4_resized
                
                # Add labels to identify each camera
                camera_status1 = "Camera 1" if ret1 else "Camera 1 (Offline)"
                camera_status2 = "Camera 2" if ret2 else "Camera 2 (Offline)"
                camera_status3 = "Camera 3" if ret3 else "Camera 3 (Offline)"
                camera_status4 = "Camera 4" if ret4 else "Camera 4 (Offline)"
                
                cv2.putText(combined_frame, camera_status1, (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if ret1 else (0, 0, 255), 2)
                cv2.putText(combined_frame, camera_status2, (cam_width + 10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if ret2 else (0, 0, 255), 2)
                cv2.putText(combined_frame, camera_status3, (10, cam_height + 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if ret3 else (0, 0, 255), 2)
                cv2.putText(combined_frame, camera_status4, (cam_width + 10, cam_height + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if ret4 else (0, 0, 255), 2)
                
                # Add grid lines for better visual separation
                cv2.line(combined_frame, (cam_width, 0), (cam_width, display_height), (255, 255, 255), 2)
                cv2.line(combined_frame, (0, cam_height), (display_width, cam_height), (255, 255, 255), 2)
                
                # Calculate and display FPS
                self.fps_frame_count += 1
                fps_current_time = time.time()
                time_diff = fps_current_time - self.fps_start_time
                
                if time_diff >= 1.0:  # Update FPS calculation every second
                    self.fps = self.fps_frame_count / time_diff
                    self.fps_frame_count = 0
                    self.fps_start_time = fps_current_time
                
                # Display FPS on the combined frame
                cv2.putText(combined_frame, f"FPS: {self.fps:.1f}", (display_width - 120, display_height - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Display the combined frame
                cv2.imshow('Quad Camera View', combined_frame)
                
                # Exit on 'q' press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # Control the frame rate to limit CPU usage
                loop_end = time.time()
                loop_time = loop_end - loop_start
                sleep_time = max(0, frame_time - loop_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        finally:
            # Release resources (except camera1 which is managed by RTSPProcessor)
            self.camera2.release()
            self.camera3.release()
            self.camera4.release()
            cv2.destroyAllWindows()
            print("Released all display resources")


class IntegratedCameraSystem:
    """Integrates RTSPProcessor and quad camera display"""
    def __init__(self, rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4, output_dir, analyze_frame):
        # Create the RTSPProcessor with analysis functionality
        self.rtsp_processor = RTSPProcessor(
            rtsp_url_1=rtsp_url1,
            rtsp_url_2=rtsp_url2,
            rtsp_url_3=rtsp_url3,
            rtsp_url_4=rtsp_url4,
            output_dir=output_dir,
            buffer_size=60,
            analysis_workers=2,
            segment_length=300,  # 5-minute segments
            reconnect_attempts=5,
            analyze_frame=analyze_frame
        )
        
        # Create the camera renderer with recording status display
        self.camera_renderer = CameraRenderWithRecordingStatus(self.rtsp_processor)
    
    def run(self):
        """Run the integrated system"""
        try:
            # Start the camera display
            self.camera_renderer.show_video()
        finally:
            # Stop the RTSPProcessor when done
            self.rtsp_processor.stop()
            print("Integrated camera system stopped")


def main():
    """Main function to run the integrated camera system"""
    from service.attendant_check import AttendantCheck
    
    # Load environment variables
    load_dotenv()
    
    # Get RTSP URLs from environment or use fallbacks
    rtsp_url1 = os.getenv('RTSP_URL1', "rtsp://admin:FFWNQY@192.168.1.2/camera/h264/ch1/main/av_stream")
    rtsp_url2 = os.getenv('RTSP_URL2', "rtsp://your_camera2_url")
    rtsp_url3 = os.getenv('RTSP_URL3', "rtsp://your_camera3_url")
    rtsp_url4 = os.getenv('RTSP_URL4', "rtsp://your_camera4_url")
    
    # Set output directory for recordings
    output_dir = "./output_video_1_cam"
    
    # Create attendant check instance
    attendant_check = AttendantCheck()
    
    try:
        # Create and run the integrated camera system
        integrated_system = IntegratedCameraSystem(
            rtsp_url1=rtsp_url1,
            rtsp_url2=rtsp_url2,
            rtsp_url3=rtsp_url3,
            rtsp_url4=rtsp_url4,
            output_dir=output_dir,
            analyze_frame=attendant_check.is_attendant_in_booth
        )
        
        integrated_system.run()
        
    except KeyboardInterrupt:
        print("Keyboard interrupt received, stopping...")
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        print("Program terminated")


if __name__ == "__main__":
    main()