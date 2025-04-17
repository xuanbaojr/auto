import cv2
import numpy as np

class Camera:
    def __init__(self, rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4):
        self.camera_render = CameraRender(rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4)

    def show_video(self):
        self.camera_render.show_video()

class CameraRender:
    def __init__(self, rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4):
        self.cap1 = cv2.VideoCapture(rtsp_url1)
        self.cap2 = cv2.VideoCapture(rtsp_url2)
        self.cap3 = cv2.VideoCapture(rtsp_url3)
        self.cap4 = cv2.VideoCapture(rtsp_url4)
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
            while True:
                # Create a blank canvas for the combined view
                combined_frame = np.zeros((display_height, display_width, 3), dtype=np.uint8)
                
                # Read frames from all cameras
                ret1, frame1 = self.cap1.read()
                ret2, frame2 = self.cap2.read()
                ret3, frame3 = self.cap3.read()
                ret4, frame4 = self.cap4.read()
                
                # Check if any camera failed to provide a frame
                if not ret1 or not ret2 or not ret3 or not ret4:
                    print("Error: Could not read frame from one or more cameras.")
                    break
                
                # Resize all frames to fit in their quadrant
                frame1_resized = cv2.resize(frame1, (cam_width, cam_height))
                frame2_resized = cv2.resize(frame2, (cam_width, cam_height))
                frame3_resized = cv2.resize(frame3, (cam_width, cam_height))
                frame4_resized = cv2.resize(frame4, (cam_width, cam_height))
                
                # Place each camera in its quadrant
                # Top-left: Camera 1
                combined_frame[0:cam_height, 0:cam_width] = frame1_resized
                # Top-right: Camera 2
                combined_frame[0:cam_height, cam_width:display_width] = frame2_resized
                # Bottom-left: Camera 3
                combined_frame[cam_height:display_height, 0:cam_width] = frame3_resized
                # Bottom-right: Camera 4
                combined_frame[cam_height:display_height, cam_width:display_width] = frame4_resized
                
                # Add labels to identify each camera
                cv2.putText(combined_frame, "Camera 1", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(combined_frame, "Camera 2", (cam_width + 10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(combined_frame, "Camera 3", (10, cam_height + 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(combined_frame, "Camera 4", (cam_width + 10, cam_height + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
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
    rtsp_url1 = "rtsp://admin:FFWNQY@192.168.1.2/camera/h264/ch1/main/av_stream"  # IP camera
    rtsp_url2 = "rtsp://admin:FFWNQY@192.168.1.2/camera/h264/ch1/main/av_stream"  # IP camera
    rtsp_url3 = "rtsp://admin:FFWNQY@192.168.1.2/camera/h264/ch1/main/av_stream"  # IP camera
    rtsp_url4 = "rtsp://localhost:8554/concatenated-sample"  # IP camera
    camera = Camera(rtsp_url1, rtsp_url2, rtsp_url3, rtsp_url4)
    camera.show_video()