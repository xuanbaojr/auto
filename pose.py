import cv2
import mediapipe as mp
import uuid
import os
import signal
import sys
import time
# from multi_camera_writer import MultiCameraWriter  # Import our new class
import logging

import cv2
import logging

logger = logging.getLogger(__name__)

class MultiCameraWriter:
    """
    VideoWriter class enhanced to support multiple camera streams simultaneously.
    """
    def __init__(self, fps=16.0):
        """
        Initialize the video writer with specified frame rate.

        Args:
            fps (float): Frame rate for recorded videos
        """
        self.fps = fps
        self.writers = {}  # Dictionary to store multiple writers
        self.is_recording = False

    def start(self, output_path, frame):
        """
        Start or continue recording a frame to the specified output path.
        Each unique path gets its own writer instance.

        Args:
            output_path (str): Path where video will be saved
            frame (ndarray): Frame to write
        """
        try:
            # If this is a new output path, initialize a writer for it
            if output_path not in self.writers:
                height, width = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use mp4v codec

                writer = cv2.VideoWriter(
                    output_path,
                    fourcc,
                    self.fps,
                    (width, height)
                )

                if not writer.isOpened():
                    raise Exception(f"Failed to open video writer for {output_path}")

                self.writers[output_path] = writer
                logger.info(f"Started new recording at {output_path}")

            # Write the frame using the appropriate writer
            self.writers[output_path].write(frame)
            self.is_recording = True

        except Exception as e:
            logger.error(f"Error in recording video to {output_path}: {e}")

    def stop(self):
        """
        Stop recording and release all writers.
        """
        try:
            for path, writer in self.writers.items():
                writer.release()
                logger.info(f"Stopped recording and saved: {path}")

            self.writers.clear()
            self.is_recording = False

        except Exception as e:
            logger.error(f"Error stopping video recording: {e}")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up directory for video storage
current_dir = os.path.dirname(__file__)
video_dir = f"{current_dir}/video"
os.makedirs(video_dir, exist_ok=True)

class PoseService:
    def __init__(self):
        """
        Initialize the pose detection service with multi-camera video recording capabilities.
        Implements the state machine for detecting person entry/exit.
        """
        # Initialize multi-camera video writer
        self.video_writer = MultiCameraWriter(fps=16.0)

        # State management
        self.same_person = False  # False = waiting for new person, True = tracking current person
        self.count_false = 0      # Counter for consecutive frames with no pose
        self.max_false = 24       # Threshold for declaring person has left (2 seconds at 24fps)
        self.session_id = None    # Current session identifier

        # Set up pose detection
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Set up signal handling for clean exit on Ctrl+C
        signal.signal(signal.SIGINT, self.handle_exit)

        # Current recording paths
        self.current_output_paths = None

        logger.info("PoseService initialized - ready to detect people")

    def check(self, frame1, frame2, frame3, frame4):
        """
        Implements the state machine for person detection and recording.

        Args:
            frame1-4: The camera frames to process from 4 different cameras

        Returns:
            str: Status message indicating current state
        """
        try:
            # Process frame to detect pose (using frame2 for detection)
            image_rgb = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
            results = self.pose.process(image_rgb)

            # Case 1: Pose detected
            if results.pose_landmarks:
                # Case 1a: New person detected
                if not self.same_person:
                    logger.info("New person detected - starting new session")

                    # Initialize new session
                    self.session_id = uuid.uuid4()
                    timestamp = time.strftime("%Y%m%d-%H%M%S")

                    # Create new output paths for this session
                    session_dir = os.path.join(video_dir, f"session_{timestamp}_{self.session_id}")
                    os.makedirs(session_dir, exist_ok=True)
                    self.current_output_paths = [
                        os.path.join(session_dir, "camera1.mp4"),
                        os.path.join(session_dir, "camera2.mp4"),
                        os.path.join(session_dir, "camera3.mp4"),
                        os.path.join(session_dir, "camera4.mp4"),
                    ]

                    # Start recording and set state
                    self.same_person = True
                    self.count_false = 0

                    # Start recording for all cameras
                    self.video_writer.start(self.current_output_paths[0], frame1)
                    self.video_writer.start(self.current_output_paths[1], frame2)
                    self.video_writer.start(self.current_output_paths[2], frame3)
                    self.video_writer.start(self.current_output_paths[3], frame4)
                    return "pose:true - new person"

                # Case 1b: Same person still present
                else:
                    # Reset false counter since we see the person
                    self.count_false = 0

                    # Continue recording all cameras
                    if self.video_writer.is_recording:
                        self.video_writer.start(self.current_output_paths[0], frame1)
                        self.video_writer.start(self.current_output_paths[1], frame2)
                        self.video_writer.start(self.current_output_paths[2], frame3)
                        self.video_writer.start(self.current_output_paths[3], frame4)

                    return "pose:true - same person"

            # Case 2: No pose detected
            else:
                # Only relevant if we were tracking someone
                if self.same_person:
                    # Increment counter of frames without pose
                    self.count_false += 1

                    # If person has been gone for max_false frames
                    if self.count_false >= self.max_false:
                        logger.info(f"Person left (no detection for {self.max_false} frames) - ending session")

                        # Stop recording and reset state
                        if self.video_writer.is_recording:
                            self.video_writer.stop()

                        # Reset state to wait for new person
                        self.same_person = False
                        self.count_false = 0
                        self.current_output_paths = None

                        return "pose:false - person left"
                    else:
                        # Person temporarily not detected, continue recording all cameras
                        if self.video_writer.is_recording:
                            self.video_writer.start(self.current_output_paths[0], frame1)
                            self.video_writer.start(self.current_output_paths[1], frame2)
                            self.video_writer.start(self.current_output_paths[2], frame3)
                            self.video_writer.start(self.current_output_paths[3], frame4)

                        return f"pose:false - temporary ({self.count_false}/{self.max_false})"

                # No one was being tracked, remain in waiting state
                return "pose:false - waiting for person"

        except Exception as e:
            logger.error(f"Error in pose detection: {e}")
            return f"error:{str(e)}"

    def handle_exit(self, sig, frame):
        """
        Handle exit signal (Ctrl+C) by properly stopping recording and cleaning up.
        """
        logger.info("Received exit signal, stopping recording and cleaning up...")

        # Stop any active recording
        if self.video_writer.is_recording:
            self.video_writer.stop()
            logger.info(f"Saved recordings: {self.current_output_paths}")

        # Release pose detection resources
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()

        logger.info("Cleanup complete")
        sys.exit(0)

def main():
    """
    Main application entry point with visualization.
    """
    try:
        # Initialize pose service
        pose_service = PoseService()

        # Initialize cameras with fallback to webcam if RTSP fails
        try:
            cap1 = cv2.VideoCapture("rtsp://localhost:8554/concatenated-sample")
            if not cap1.isOpened():
                logger.warning("Failed to open RTSP stream 1, falling back to webcam")
                cap1 = cv2.VideoCapture(0)
        except Exception as e:
            logger.warning(f"Error opening RTSP stream 1: {e}, falling back to webcam")
            cap1 = cv2.VideoCapture(0)

        # Local camera
        cap2 = cv2.VideoCapture(0)

        try:
            cap3 = cv2.VideoCapture("rtsp://localhost:8554/concatenated-sample")
            if not cap3.isOpened():
                logger.warning("Failed to open RTSP stream 3, falling back to webcam")
                cap3 = cv2.VideoCapture(0)
        except Exception as e:
            logger.warning(f"Error opening RTSP stream 3: {e}, falling back to webcam")
            cap3 = cv2.VideoCapture(0)

        try:
            cap4 = cv2.VideoCapture("rtsp://localhost:8554/concatenated-sample")
            if not cap4.isOpened():
                logger.warning("Failed to open RTSP stream 4, falling back to webcam")
                cap4 = cv2.VideoCapture(0)
        except Exception as e:
            logger.warning(f"Error opening RTSP stream 4: {e}, falling back to webcam")
            cap4 = cv2.VideoCapture(0)

        # Check if all cameras opened successfully
        if not cap1.isOpened() or not cap2.isOpened() or not cap3.isOpened() or not cap4.isOpened():
            logger.error("Failed to open one or more cameras")
            return

        logger.info("All cameras initialized - press 'q' to quit or Ctrl+C to save and exit")

        # For FPS calculation
        frame_count = 0
        start_time = time.time()
        fps = 0

        # Main processing loop
        while True:
            # Capture frames from all cameras
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()
            ret3, frame3 = cap3.read()
            ret4, frame4 = cap4.read()

            # Resize all frames to 1920x1080
            # frame1 = cv2.resize(frame1, (1920, 1080))
            frame2 = cv2.resize(frame2, (1080, 720))
            # frame3 = cv2.resize(frame3, (1920, 1080))
            # frame4 = cv2.resize(frame4, (1920, 1080))

            # If any camera failed to capture, use a placeholder or previous frame
            if not ret1 or not ret2 or not ret3 or not ret4:
                logger.warning("Failed to capture frames from one or more cameras")
                # Generate placeholder frames for failed captures
                if not ret1:
                    frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame1, "Camera 1 - No Signal", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                if not ret2:
                    frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame2, "Camera 2 - No Signal", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                if not ret3:
                    frame3 = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame3, "Camera 3 - No Signal", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                if not ret4:
                    frame4 = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame4, "Camera 4 - No Signal", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Process the frames - use frame2 (webcam) for pose detection
            # but send all frames for recording
            status = pose_service.check(frame1, frame2, frame3, frame4)

            # Calculate FPS
            frame_count += 1
            elapsed_time = time.time() - start_time
            if elapsed_time >= 1.0:
                fps = frame_count / elapsed_time
                frame_count = 0
                start_time = time.time()

            # Create a combined display frame
            # Display status on frame
            cv2.putText(
                frame2,
                f"Status: {status}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            # Recording indicator
            if pose_service.same_person:
                indicator_color = (0, 255, 0) if pose_service.count_false == 0 else (0, 165, 255)
                cv2.putText(
                    frame2,
                    "RECORDING" if pose_service.video_writer.is_recording else "ERROR",
                    (frame2.shape[1] - 150, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    indicator_color,
                    2
                )

                # Session info
                if pose_service.session_id:
                    cv2.putText(
                        frame2,
                        f"Session: {str(pose_service.session_id)[:8]}",
                        (10, frame2.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        1
                    )

            # FPS counter
            cv2.putText(
                frame2,
                f"FPS: {fps:.1f}",
                (frame2.shape[1] - 100, frame2.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1
            )

            try:
                # Display the monitoring frame (webcam)
                cv2.imshow("Person Detection", frame2)
            except Exception as e:
                logger.error(f"Error displaying frame: {e}")
                # If we can't display the frame, we'll just continue without the GUI
                # This allows the application to run in headless mode if needed

            try:
                # Check for user input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
            except Exception as e:
                # If waitKey fails, we'll check for keyboard interrupt in the outer loop
                logger.warning(f"Error in waitKey: {e}")
                # Sleep a bit to prevent CPU overuse
                time.sleep(0.01)

    except KeyboardInterrupt:
        logger.info("User interrupted program with Ctrl+C")
        # The signal handler will handle cleanup

    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    finally:
        # Ensure cleanup happens even if unexpected errors occur
        # Release all camera resources
        for cap in [cap1, cap2, cap3, cap4]:
            if cap is not None:
                cap.release()

        cv2.destroyAllWindows()

        # Final cleanup if pose_service exists
        if 'pose_service' in locals() and pose_service.video_writer.is_recording:
            pose_service.video_writer.stop()

        logger.info("Program ended")

if __name__ == "__main__":
    # Import numpy for placeholder frames if needed
    import numpy as np
    main()