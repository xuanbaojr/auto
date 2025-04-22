from degree_model import FaceInfo

class FaceTopCheck:

    def __init__(self):
        self.face_info = FaceInfo()
        self.target_pitch = 0.5
        self.min_yaw = -10
        self.max_yaw = 10

    def check(self, frame):
        pitch, roll, yaw, _ = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
            if self.min_yaw < yaw < self.max_yaw and pitch == self.target_pitch:
                return True
        return False
            