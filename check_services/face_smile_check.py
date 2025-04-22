from degree_model import FaceInfo
class FaceSmileCheck:

    def __init__(self):
        self.face_info = FaceInfo()
        self.min_yaw = -10
        self.max_yaw = 10
        self.min_pitch = 0.5
        self.max_pitch = 1.5

    def check(self, frame):
        pitch, roll, yaw, smile_ratio = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
            if self.min_yaw < yaw < self.max_yaw and self.min_pitch < pitch < self.max_pitch:
                if smile_ratio > 0.5:
                    return True
        return False
            