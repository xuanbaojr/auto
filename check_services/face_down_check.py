<<<<<<< HEAD
class FaceDownCheck:
    def __init__(self, face_info):
        self.face_info = face_info
        self.target_pitch = 2
        self.min_yaw = -150
        self.max_yaw = 150
=======
from degree_model import FaceInfo

class FaceDownCheck:
    def __init__(self):
        self.face_info = FaceInfo()
        self.target_pitch = 1.5
        self.min_yaw = -10
        self.max_yaw = 10
>>>>>>> 30669cd40155d41f89fabcc3a13a39a06a37a0de

    def check(self, frame):
        pitch, roll, yaw, _ = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
<<<<<<< HEAD
            if self.min_yaw < yaw < self.max_yaw and pitch > self.target_pitch:
=======
            if self.min_yaw < yaw < self.max_yaw and pitch == self.target_pitch:
>>>>>>> 30669cd40155d41f89fabcc3a13a39a06a37a0de
                return True
        return False
            