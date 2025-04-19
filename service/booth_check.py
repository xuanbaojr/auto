import mediapipe as mp
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

class PoseService:
    def __init__(self):
        """
        Initialize the pose detection service with multi-camera video recording capabilities.
        Implements the state machine for detecting person entry/exit.
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.15,
            min_tracking_confidence=0.7
        )

    
    def get_pose(self, frame):
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        result = "1" if results.pose_landmarks else "0"
        return result

class BoothCheck:
    def __init__(self):
        self.pose_service = PoseService()
        self.person_frames_threshold = 5  # Detect person after this many frames
        self.no_person_frames_threshold = 20  # Declare no person after this many frames
        self.person_frame_count = 0
        self.no_person_frame_count = 0
        self.person_present = False

    def check(self, frame):
        result = self.pose_service.get_pose(cv2.resize(frame, (2560//3, 1440//3)))
    
        if result == "1":  # Person detected
            self.person_frame_count += 1
            self.no_person_frame_count = 0
            
            # Require multiple consecutive frames with a person for stability
            if self.person_frame_count >= self.person_frames_threshold:
                self.person_present = True
        else:  # No person detected
            self.no_person_frame_count += 1
            self.person_frame_count = 0
            
            # Require multiple consecutive frames without a person for stability
            if self.no_person_frame_count >= self.no_person_frames_threshold:
                self.person_present = False
        return self.person_present
    

if __name__ == "__main__":
    booth_check = BoothCheck()
    cap = Camera("rtsp://admin:FFWNQY@192.168.1.2/camera/h264/ch1/main/av_stream")  # Use 0 for the default camera
    while True:
        frame = cap.getFrame()           #2560. 1440

        if frame is None:
            continue
        result = booth_check.check(frame)
        result_print = "1" if result else "00000000000000000000000000000000000"
        print(result_print)
        cv2.imshow('frame', cv2.resize(frame, (2560//3, 1440//3)))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()