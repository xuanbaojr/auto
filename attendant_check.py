from check_services.booth_check import BoothCheck
from check_services.hand_check import HandCheck
from check_services.body_face_forward_check import BodyFaceForwardCheck
from check_services.face_top_check import FaceTopCheck
from check_services.face_down_check import FaceDownCheck
from check_services.face_left_check import FaceLeftCheck
from check_services.face_right_check import FaceRightCheck
from check_services.face_smile_check import FaceSmileCheck
from check_services.body_face_behind_check import BodyFaceBehindCheck
from check_services.body_face_left_check import BodyFaceLeftCheck
from check_services.body_face_right_check import BodyFaceRightCheck

class AttendantCheck:
    def __init__(self):
        self.booth_check = BoothCheck()
        self.hand_check = HandCheck()
        self.body_face_forward_check = BodyFaceForwardCheck()
        self.face_top_check = FaceTopCheck()
        self.face_down_check = FaceDownCheck()
        self.face_left_check = FaceLeftCheck()
        self.face_right_check = FaceRightCheck()
        self.face_smile_check = FaceSmileCheck()
        self.body_face_behind_check = BodyFaceBehindCheck()
        self.body_face_left_check = BodyFaceLeftCheck()
        self.body_face_right_check = BodyFaceRightCheck()
    
    def check(self, frame1, frame2, frame3, frame4, just_checked):
        if just_checked == 0:
            return self.booth_check.check(frame1)
        elif just_checked == 1:
            return self.hand_check.check(frame4)
        elif just_checked == 2:
            return self.body_face_forward_check.check(frame1)
        elif just_checked == 3:
            return self.face_top_check.check(frame1)
        elif just_checked == 4:
            return self.face_down_check.check(frame1)
        elif just_checked == 5:
            return self.face_left_check.check(frame1)
        elif just_checked == 6:
            return self.face_right_check.check(frame1)
        elif just_checked == 7:
            return self.face_smile_check.check(frame1)
        elif just_checked == 8:
            return self.body_face_behind_check.check(frame1)
        elif just_checked == 9:
            return self.body_face_left_check.check(frame1)
        elif just_checked == 10:
            return self.body_face_right_check.check(frame1)

  