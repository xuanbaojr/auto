import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2

class BodyFaceBehindCheck:
    def __init__(self, detector):
        self.detector = detector

    def get_points(self, frame_shape, landmark):
        h, w, _ = frame_shape
        x = int(landmark.x * w)
        y = int(landmark.y * h)

        return (x, y)

    def check_behind(self, frame_shape, left_shoulder, right_shoulder, mid_head):
        left_shoulder_x, left_shoulder_y = self.get_points(frame_shape, left_shoulder)
        right_shoulder_x, right_shoulder_y = self.get_points(frame_shape, right_shoulder)
        mid_head_x, mid_head_y = self.get_points(frame_shape, mid_head)

        if (left_shoulder_x > right_shoulder_x and left_shoulder_x == right_shoulder_x):
            return False
        
        elif (left_shoulder_x < right_shoulder_x):
            mid_shoulder_x = (left_shoulder_x + right_shoulder_x) / 2
            dist = abs(mid_head_x - mid_shoulder_x)
            return 50 <  dist < 250
        
        return False
        

    def check(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_shape = frame_rgb.shape

        mp_frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        pose_landmarker_result = self.detector.detect(mp_frame)

        if pose_landmarker_result.pose_landmarks:
            landmarks = pose_landmarker_result.pose_landmarks[0]
        else:
            print("Can not find landmarks")
            return False
        
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        mid_head = landmarks[0]

        is_behind = self.check_behind(frame_shape, left_shoulder, right_shoulder, mid_head)
        print(f"behind: {is_behind}")
        
        return is_behind
            