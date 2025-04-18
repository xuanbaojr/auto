import cv2
import numpy as np

class Camera:
    def __init__(self, rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4):
        self.camera_render = CameraRender(rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4)

    def show_video(self):
        self.camera_render.show_video()

class CameraRender:
    def __init__(self, rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4):
        # Store URLs for reconnection purposes
        self.rtsp_url1 = rtsp_url1
        self.rtsp_url2 = rtsp_url2
        self.rtsp_url3 = rtsp_url3
        self.rtsp_url4 = rtsp_url4
        
        # Try to connect to cameras
        self._connect_cameras()
    
    def _connect_cameras(self):
        """Initialize connections to all cameras with proper parameters"""
        # Set OpenCV VideoCapture properties for better performance
        self.cap1 = cv2.VideoCapture(self.rtsp_url1)
        self.cap1.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # Reduce buffer size
        
        self.cap2 = cv2.VideoCapture(self.rtsp_url2)
        self.cap2.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        
        self.cap3 = cv2.VideoCapture(self.rtsp_url3)
        self.cap3.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        
        self.cap4 = cv2.VideoCapture(self.rtsp_url4)
        self.cap4.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        
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
        
        try:
            frame_count = 0
            while True:
                frame_count += 1
                
                # Create a blank canvas for the combined view
                combined_frame = np.zeros((display_height, display_width, 3), dtype=np.uint8)
                
                # Read frames from all cameras and handle potential failures
                ret1, frame1 = self.cap1.read()
                ret2, frame2 = self.cap2.read()
                ret3, frame3 = self.cap3.read()
                ret4, frame4 = self.cap4.read()
                
                # Reconnect cameras if needed (every 30 frames check)
                if frame_count % 30 == 0:
                    if not ret1:
                        print("Reconnecting to Camera 1...")
                        self.cap1.release()
                        self.cap1 = cv2.VideoCapture(self.rtsp_url1)
                    if not ret2:
                        print("Reconnecting to Camera 2...")
                        self.cap2.release()
                        self.cap2 = cv2.VideoCapture(self.rtsp_url2)
                    if not ret3:
                        print("Reconnecting to Camera 3...")
                        self.cap3.release()
                        self.cap3 = cv2.VideoCapture(self.rtsp_url3)
                    if not ret4:
                        print("Reconnecting to Camera 4...")
                        self.cap4.release()
                        self.cap4 = cv2.VideoCapture(self.rtsp_url4)
                
                # Prepare fallback frame for missing cameras
                fallback_frame = np.zeros((cam_height, cam_width, 3), dtype=np.uint8)
                cv2.putText(fallback_frame, "Camera Unavailable", (10, cam_height//2), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Process each camera feed individually
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
                
                # Display the combined frame
                cv2.imshow('Quad Camera View', combined_frame)
                
                # Exit on 'q' press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            # Release resources outside the loop
            self.cap1.release()
            self.cap2.release()
            self.cap3.release()
            self.cap4.release()
            cv2.destroyAllWindows()
            print("Released all resources")

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