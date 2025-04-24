class FaceSmileCheck:

    def __init__(self, face_info):
        self.face_info = face_info
        self.min_yaw = -150
        self.max_yaw = 150
        self.min_pitch = 0.3
        self.max_pitch = 1.8


    def check(self, frame):
        pitch, roll, yaw, smile_ratio = self.face_info.get_face_info(frame)
        if pitch is not None and roll is not None and yaw is not None:
            if self.min_yaw < yaw < self.max_yaw and self.min_pitch < pitch < self.max_pitch:
                if smile_ratio > 0.88:
                    return True
        return False
            