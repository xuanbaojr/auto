import os
import cv2
import mediapipe as mp

class PoseService:
    def __init__(self, detector):        
        self.detector = detector
    
    def get_pose(self, frame):
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        pose_landmarker_result = self.detector.detect(mp_frame)
        if pose_landmarker_result.pose_landmarks:
            return "1"
        else:
            return "0"

class BoothCheck:
    def __init__(self, detector):
        self.pose_service = PoseService(detector)
        self.person_frames_threshold = 1  # Detect person after this many frames
        self.no_person_frames_threshold = 1  # Declare no person after this many frames
        self.person_frame_count = 0
        self.no_person_frame_count = 0
        self.person_present = False

    def check(self, frame):
        result = self.pose_service.get_pose(cv2.resize(frame, (2560//3, 1440//3)))
    
        if result == "1":  # Person detected
            self.person_frame_count += 1
            self.no_person_frame_count = 0
            
            # Require multiple consecutive frames with a person for stability
            if self.person_frame_count >= self.person_frames_threshold:
                self.person_present = True
        else:  # No person detected
            self.no_person_frame_count += 1
            self.person_frame_count = 0
            
            # Require multiple consecutive frames without a person for stability
            if self.no_person_frame_count >= self.no_person_frames_threshold:
                self.person_present = False
        return self.person_present