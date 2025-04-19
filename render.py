import cv2
import numpy as np
import threading
from threading import Lock
import time

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
        self.thread = threading.Thread(target=self.rtsp_cam_buffer, name=f"rtsp_thread_{name}")
        self.thread.daemon = True
        self.thread.start()
    
    def rtsp_cam_buffer(self):
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

class CameraRender:
    def __init__(self, rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4):
        # Initialize camera objects with threading
        self.camera1 = ThreadedCamera(rtsp_url1, "Camera 1")
        self.camera2 = ThreadedCamera(rtsp_url2, "Camera 2")
        self.camera3 = ThreadedCamera(rtsp_url3, "Camera 3")
        self.camera4 = ThreadedCamera(rtsp_url4, "Camera 4")
        
        # Performance tracking
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.fps = 0
    
    def show_video(self):
        """
        Display feeds from 4 cameras in a 2x2 grid layout.
        Each camera occupies one quarter of the screen.
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
            # Release resources
            self.camera1.release()
            self.camera2.release()
            self.camera3.release()
            self.camera4.release()
            cv2.destroyAllWindows()
            print("Released all resources")

class Camera:
    def __init__(self, rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4):
        self.camera_render = CameraRender(rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4)

    def show_video(self):
        self.camera_render.show_video()

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()  # Load environment variables from .env file

    rtsp_url1 = os.getenv('RTSP_URL1')
    rtsp_url2 = os.getenv('RTSP_URL2')
    rtsp_url3 = os.getenv('RTSP_URL3')
    rtsp_url4 = os.getenv('RTSP_URL4')

    camera = Camera(rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4)
    camera.show_video()