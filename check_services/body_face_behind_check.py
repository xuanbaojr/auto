<<<<<<< HEAD
import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import threading
from threading import Lock

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


class BodyFaceBehindCheck:
    def __init__(self, detector):
        self.detector = detector

    def get_points(self, frame_shape, landmark):
        h, w, _ = frame_shape
        x = int(landmark.x * w)
        y = int(landmark.y * h)

        return (x, y)

    def check_behind(self, frame_shape, left_shoulder, right_shoulder, mid_head):
        left_shoulder_x, left_shoulder_y = self.get_points(frame_shape, left_shoulder)
        right_shoulder_x, right_shoulder_y = self.get_points(frame_shape, right_shoulder)
        mid_head_x, mid_head_y = self.get_points(frame_shape, mid_head)

        if (left_shoulder_x > right_shoulder_x and left_shoulder_x == right_shoulder_x):
            return False
        
        elif (left_shoulder_x < right_shoulder_x):
            
            mid_shoulder_x = (left_shoulder_x + right_shoulder_x) / 2
            dist = abs(mid_head_x - mid_shoulder_x)
            print(dist)
            return dist < 100
        
        return False
        

    def check(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_shape = frame_rgb.shape

        mp_frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        pose_landmarker_result = self.detector.detect(mp_frame)

        if pose_landmarker_result.pose_landmarks:
            landmarks = pose_landmarker_result.pose_landmarks[0]
        else:
            print("Can not find landmarks")
            return False
        
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        mid_head = landmarks[0]

        is_behind = self.check_behind(frame_shape, left_shoulder, right_shoulder, mid_head)        
        return is_behind

if __name__ == "__main__":
    base_optimions = python.BaseOptions(model_asset_path="./checkpoints/pose_landmarker_heavy.task")
    options = vision.PoseLandmarkerOptions(
        base_options=base_optimions,
        output_segmentation_masks=True)
    detector = vision.PoseLandmarker.create_from_options(options)
    body_face_behind_check = BodyFaceBehindCheck(detector)
    from dotenv import load_dotenv
    import os
    load_dotenv()
    rtsp_url1 = os.getenv('RTSP_URL1')
    cap = Camera(rtsp_url1)
    while True:
        frame = cap.getFrame()

        if frame is None:
            continue
        frame = frame[:, 200:2200]
        frame = cv2.resize(frame, (2560//3, 1440//3))
        is_behind = body_face_behind_check.check(frame)
        cv2.imshow('frame', frame)
        if cv2.waitKey(1) == ord('q'):
            break
=======
class BodyFaceBehindCheck:
    def __init__(self):
        pass
    def check(self, frame):
        for i in range(5000):
            continue
        return False
            
>>>>>>> 30669cd40155d41f89fabcc3a13a39a06a37a0de
