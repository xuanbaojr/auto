<<<<<<< HEAD
class FaceRightCheck:

    def __init__(self, face_info):
        self.face_info = face_info
        self.target_yaw = -25
        self.min_pitch = 0.3
        self.max_pitch = 1.8
=======
from degree_model import FaceInfo
class FaceRightCheck:

    def __init__(self):
        self.face_info = FaceInfo()
        self.target_yaw = -40
        self.min_pitch = 0.5
        self.max_pitch = 1.5
>>>>>>> 30669cd40155d41f89fabcc3a13a39a06a37a0de

    def check(self, frame):
        pitch, roll, yaw, _ = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
<<<<<<< HEAD
            if yaw <= self.target_yaw and self.min_pitch < pitch < self.max_pitch:
=======
            if yaw == self.target_yaw and self.min_pitch < pitch < self.max_pitch:
>>>>>>> 30669cd40155d41f89fabcc3a13a39a06a37a0de
                return True
        return False
            