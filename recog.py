import cv2
import numpy as np
import time
import os
import logging
from typing import Tuple, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VideoWriter:
    """
    Enhanced video writer with error handling and codec fallbacks.
    """
    def __init__(self, fps: float = 30.0, resolution: Optional[Tuple[int, int]] = None):
        """
        Initialize the video writer with better defaults and type hints.
        
        Args:
            fps: Frames per second for the output video
            resolution: Optional (width, height) tuple; if None, determined from first frame
        """
        self.fps = fps
        self.resolution = resolution
        self.writer = None
        self.is_recording = False
        self.output_path = None
        
        # List of codecs to try in order of preference
        self.codec_options = [
            ('avc1', '.mp4'),  # H.264 in MP4 (widely supported)
            ('mp4v', '.mp4'),  # MPEG-4 (good compatibility)
            ('XVID', '.avi'),  # XVID in AVI (very compatible)
            ('MJPG', '.avi'),  # Motion JPEG (fallback)
        ]
        
    def start(self, output_path, frame: np.ndarray) -> bool:
        """
        Start recording with the given frame, trying multiple codecs if needed.
        Also writes the initial frame automatically.
        
        Args:
            output_path: Path where the video will be saved
            frame: Initial video frame that determines dimensions if not specified
            
        Returns:
            bool: True if recording started successfully, False otherwise
        """
        self.output_path = output_path
        
        # If already recording, handle the frame writing directly
        if self.is_recording:
            logger.warning("Recording already in progress")
            if self.writer is not None:
                try:
                    self.writer.write(frame)
                    logger.debug("Frame written to existing recording")
                    return True
                except Exception as e:
                    logger.error(f"Error writing frame to existing recording: {str(e)}")
                    return False
            return True
            
        # Get frame dimensions for the video
        h, w = frame.shape[:2]
        if self.resolution:
            w, h = self.resolution
        
        # Try each codec until one works
        for codec_fourcc, extension in self.codec_options:
            try:
                # Update file extension based on codec
                base_path = os.path.splitext(self.output_path)[0]
                current_path = f"{base_path}{extension}"
                
                fourcc = cv2.VideoWriter_fourcc(*codec_fourcc)
                writer = cv2.VideoWriter(current_path, fourcc, self.fps, (w, h))
                
                # Test if the writer is initialized properly
                if writer.isOpened():
                    self.writer = writer
                    self.output_path = current_path
                    self.is_recording = True
                    logger.info(f"Recording started: {self.output_path} with codec {codec_fourcc}")
                    
                    # Integrated frame writing - write the initial frame immediately
                    try:
                        self.writer.write(frame)
                        logger.debug("Initial frame written successfully")
                    except Exception as e:
                        logger.error(f"Error writing initial frame: {str(e)}")
                        # Continue even if writing initial frame fails
                        
                    return True
                else:
                    writer.release()
            except Exception as e:
                logger.warning(f"Failed to initialize with codec {codec_fourcc}: {str(e)}")
        
        logger.error("Failed to start recording with any available codec")
        return False
            
    def stop(self) -> None:
        """
        Stop recording and release resources safely.
        """
        if not self.is_recording or self.writer is None:
            return
            
        try:
            self.writer.release()
            logger.info(f"Recording stopped: {self.output_path}")
        except Exception as e:
            logger.error(f"Error stopping recording: {str(e)}")
        finally:
            self.writer = None
            self.is_recording = False

def main():
    """
    Main application function with improved error handling.
    """
    # Create output directory if it doesn't exist
    output_dir = "videos"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize camera with error handling
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Failed to open camera")
            return
    except Exception as e:
        logger.error(f"Error initializing camera: {str(e)}")
        return
        
    # Get initial frame to check if camera works
    ret, frame = cap.read()
    if not ret or frame is None:
        logger.error("Failed to capture initial frame")
        cap.release()
        return
        
    # Initialize video writer
    video_writer = VideoWriter()
    
    # Display controls
    logger.info("Controls:")
    logger.info(" 'r' - Start/stop recording")
    logger.info(" 'q' - Quit")
    
    recording_status_text = "NOT RECORDING"
    text_color = (0, 0, 255)  # Red for not recording
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to capture frame, exiting...")
                break
                
            # Add recording status to the frame
            cv2.putText(
                frame, 
                recording_status_text, 
                (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                text_color, 
                2
            )
            
            # For continuous recording, call start again with each frame
            # This handles both initialization and frame writing
            if video_writer.is_recording:
                video_writer.start(video_writer.output_path, frame)
                
            # Display the frame
            cv2.imshow("Camera Feed", frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                if video_writer.is_recording:
                    video_writer.stop()
                    recording_status_text = "NOT RECORDING"
                    text_color = (0, 0, 255)  # Red
                else:
                    # Create a new file for each recording
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    output_path = os.path.join(output_dir, f"video_{timestamp}.mp4")
                    if video_writer.start(output_path, frame):
                        recording_status_text = "RECORDING"
                        text_color = (0, 255, 0)  # Green
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        # Clean up
        video_writer.stop()
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Program ended")

if __name__ == "__main__":
    main()