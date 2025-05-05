class FaceRightCheck:

    def __init__(self, face_info):
        self.face_info = face_info
        self.target_yaw = -25
        self.min_pitch = 0.3
        self.max_pitch = 1.8

    def check(self, frame):
        pitch, roll, yaw, _ = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
            if yaw <= self.target_yaw and self.min_pitch < pitch < self.max_pitch:
                return True
        return False
            