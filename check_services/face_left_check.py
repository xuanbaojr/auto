from degree_model import FaceInfo

class FaceLeftCheck:

    def __init__(self):
        self.face_info = FaceInfo()
        self.target_yaw = 40
        self.min_pitch = 0.5
        self.max_pitch = 1.5

    def check(self, frame):
        pitch, roll, yaw, _ = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
            if yaw == self.target_yaw and self.min_pitch < pitch < self.max_pitch:
                return True
        return False
            