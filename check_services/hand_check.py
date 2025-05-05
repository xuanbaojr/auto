import cv2
import mediapipe as mp

class HandCheck:
<<<<<<< HEAD
    def __init__(self, mp_hands):
        self.mp_hands = mp_hands
=======
    def __init__(self):
        self.mp_hands = mp.solutions.hands
>>>>>>> 30669cd40155d41f89fabcc3a13a39a06a37a0de
    def check(self, frame):
        total_keypoints = 0

        with self.mp_hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.2) as hands:
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(image_rgb)

            if results.multi_hand_landmarks is not None:
                for hand_landmarks in results.multi_hand_landmarks:
                    total_keypoints += len(hand_landmarks.landmark)  # mỗi bàn tay có 21 điểm            if total_keypoints == 42:
        if total_keypoints == 42:
            return True
        else:
            return False
            