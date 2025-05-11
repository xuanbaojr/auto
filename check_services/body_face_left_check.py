import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2

class BodyFaceLeftCheck:
    def __init__(self, face_info):
        self.face_info = face_info
        self.min_yaw = 50
        self.min_pitch = 0.2
        self.max_pitch = 1.8

    def check(self, frame):
        pitch, roll, yaw, smile_ratio = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
            if self.min_yaw < yaw and self.min_pitch < pitch < self.max_pitch:
                return True
        return False
