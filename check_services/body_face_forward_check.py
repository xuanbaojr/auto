<<<<<<< HEAD
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2

class BodyFaceForwardCheck:
    def __init__(self, face_info):
        self.face_info = face_info
        self.min_yaw = -50
        self.max_yaw = 50
        self.min_pitch = 0.5
        self.max_pitch = 1.5

    def check(self, frame):
        pitch, roll, yaw, smile_ratio = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
            if self.min_yaw < yaw < self.max_yaw and self.min_pitch < pitch < self.max_pitch:
                return True
        return False
    
if __name__ == "__main__":
    base_optimions = python.BaseOptions(model_asset_path="./checkpoints/pose_landmarker_heavy.task")
    options = vision.PoseLandmarkerOptions(
        base_options=base_optimions,
        output_segmentation_masks=True)
    detector = vision.PoseLandmarker.create_from_options(options)
    body_face_forward_check = BodyFaceForwardCheck(detector)
    cap = cv2.VideoCapture("./cam1_2.mp4")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        is_forward = body_face_forward_check.check(frame)
        print(is_forward)
        cv2.imshow('frame', cv2.resize(frame, (1366//2, 768//2)))
        if cv2.waitKey(1) == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
=======
class BodyFaceForwardCheck:
    def __init__(self):
        pass
    def check(self, frame):
        for i in range(10000):
            continue
        return False
            
>>>>>>> 30669cd40155d41f89fabcc3a13a39a06a37a0de
