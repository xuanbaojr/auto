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


import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from check_services.degree_model import FaceInfo

class AttendantCheck:
    def __init__(self):
        # body_face_check
        base_optimions = python.BaseOptions(model_asset_path="./check_services/checkpoints/pose_landmarker_heavy.task")
        self.options = vision.PoseLandmarkerOptions(
            base_options=base_optimions,
            output_segmentation_masks=True)
        detector = vision.PoseLandmarker.create_from_options(self.options)

        # face_check
        face_info = FaceInfo()

        # hand_check
        mp_hands = mp.solutions.hands

        self.booth_check = BoothCheck(detector)
        self.hand_check = HandCheck(mp_hands)
        self.body_face_forward_check = BodyFaceForwardCheck(detector)
        self.face_top_check = FaceTopCheck(face_info)
        self.face_down_check = FaceDownCheck(face_info)
        self.face_left_check = FaceLeftCheck(face_info)
        self.face_right_check = FaceRightCheck(face_info)
        self.face_smile_check = FaceSmileCheck(face_info)
        self.body_face_behind_check = BodyFaceBehindCheck(detector)
        self.body_face_left_check = BodyFaceLeftCheck(detector)
        self.body_face_right_check = BodyFaceRightCheck(detector)

        

    
    def check(self, frame1, frame2, frame3, frame4, just_checked):
        print("just_checked: ", just_checked)
        if just_checked == 0:
            return self.booth_check.check(frame1)
        elif just_checked == 1:
            return self.hand_check.check(frame1)          # frame4
        elif just_checked == 2:
            return self.body_face_forward_check.check(frame1)
        elif just_checked == 3:
            return self.face_top_check.check(frame1)
        elif just_checked == 4:
            return self.face_right_check.check(frame1)
        elif just_checked == 5:
            return self.face_down_check.check(frame1)
        elif just_checked == 6:
            return self.face_left_check.check(frame1)
        elif just_checked == 7:
            return self.face_smile_check.check(frame1)
        elif just_checked == 8:
            return self.body_face_right_check.check(frame1)
        elif just_checked == 9:
            return self.body_face_behind_check.check(frame1)
        elif just_checked == 10:
            return self.body_face_left_check.check(frame1)

  