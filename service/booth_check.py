import mediapipe as mp
import cv2

class PoseService:
    def __init__(self):
        """
        Initialize the pose detection service with multi-camera video recording capabilities.
        Implements the state machine for detecting person entry/exit.
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    
    def get_pose(self, frame):
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        return results.pose_landmarks

class BoothCheck:
    def __init__(self):
        self.pose_service = PoseService()
        self.count_false = 0
        self.max_false = 24

    def check(self, frame):
        result = self.pose_service.get_pose(frame)
        if result:
            self.count_false = 0
            return True
        elif not result:
            self.count_false += 1
            if self.count_false >= self.max_false:
                self.count_false = 0
                return False
        return True
    
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    booth_check = BoothCheck()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        result = booth_check.check(frame)
        print(result)
        cv2.imshow('frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()