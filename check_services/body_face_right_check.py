<<<<<<< HEAD
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2

class BodyFaceRightCheck:
    def __init__(self, face_info):
        self.face_info = face_info
        self.min_yaw = -60
        self.min_pitch = 0.2
        self.max_pitch = 1.8

    def check(self, frame):
        pitch, roll, yaw, smile_ratio = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
            if yaw < self.min_yaw and self.min_pitch < pitch < self.max_pitch:
                return True
        return False
=======
class BodyFaceRightCheck:
    def __init__(self):
        pass
    def check(self, frame):
        for i in range(10000):
            continue
        return False
            
>>>>>>> 30669cd40155d41f89fabcc3a13a39a06a37a0de
