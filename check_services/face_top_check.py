
class FaceTopCheck:

    def __init__(self, face_info):
        self.face_info = face_info
        self.target_pitch = 0.6
        self.min_yaw = -150
        self.max_yaw = 150

    def check(self, frame):
        pitch, roll, yaw, _ = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
            if self.min_yaw < yaw < self.max_yaw and pitch < self.target_pitch:
                return True
        return False
            