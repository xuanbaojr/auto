import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2

class BodyFaceLeftCheck:
    def __init__(self):
        base_options = python.BaseOptions(model_asset_path="./check_services/checkpoints/pose_landmarker_heavy.task")
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=True)
        self.detector = vision.PoseLandmarker.create_from_options(options)

    def get_points(self, frame_shape, landmark):
        h, w, _ = frame_shape
        x = int(landmark.x * w)
        y = int(landmark.y * h)

        return (x, y)

    def check_left(self, frame_shape, left_shoulder, right_shoulder, mid_head):
        left_shoulder_x, left_shoulder_y = self.get_points(frame_shape, left_shoulder)
        right_shoulder_x, right_shoulder_y = self.get_points(frame_shape, right_shoulder)
        mid_head_x, mid_head_y = self.get_points(frame_shape, mid_head)

        subtraction = abs(left_shoulder_x - right_shoulder_x)
        if subtraction < 30 and mid_head_x > left_shoulder_x:
            return True

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

        is_left = self.check_left(frame_shape, left_shoulder, right_shoulder, mid_head)
        print(f"Left: {is_left}")
        
        return is_left
            