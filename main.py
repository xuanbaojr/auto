import cv2
import gradio as gr
import time
import logging

# Configure logging for production use
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('webcam_stream')

# Configuration parameters - easily adjustable
WEBCAM_ID = 0        # Default camera (built-in webcam is usually 0)
FRAME_RATE = 30      # Target FPS
RESOLUTION = (1080, 960)  # Width x Height

RTSP_LINKS = [
    "rtsp://localhost:8554/concatenated-sample",
    "rtsp://localhost:8554/concatenated-sample",
    "rtsp://localhost:8554/concatenated-sample",
]

def webcam_feed():
    """
    Generator function that continuously yields frames from the webcam.
    This approach is memory-efficient as it processes one frame at a time.
    """
    logger.info("Starting webcam feed")
    
    # Initialize webcam with specified device ID
    cap = cv2.VideoCapture(WEBCAM_ID)
    rtsp2_vid = cv2.VideoCapture(RTSP_LINKS[0])
    rtsp3_vid = cv2.VideoCapture(RTSP_LINKS[1])
    rtsp4_vid = cv2.VideoCapture(RTSP_LINKS[2])

    
    # Set resolution for consistent output
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
    rtsp2_vid.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
    rtsp2_vid.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
    rtsp3_vid.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
    rtsp3_vid.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
    rtsp4_vid.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
    rtsp4_vid.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
    
    # Verify camera connection
    if not cap.isOpened():
        logger.error(f"Failed to open webcam with ID {WEBCAM_ID}")
        raise RuntimeError(f"Could not open webcam with ID {WEBCAM_ID}. Please check connection.")
    
    logger.info(f"Webcam initialized successfully at {RESOLUTION[0]}x{RESOLUTION[1]}")
    
    try:
        while True:
            ret, frame = cap.read()
            ret2, frame2 = rtsp2_vid.read()
            ret3, frame3 = rtsp3_vid.read()
            ret4, frame4 = rtsp4_vid.read()
            if not ret2:
                logger.error("Failed to grab frame from rtsp2")
                break
            if not ret3:
                logger.error("Failed to grab frame from rtsp3")
                break
            if not ret4:
                logger.error("Failed to grab frame from rtsp4")
                break
            
            if not ret:
                logger.error("Failed to grab frame from webcam")
                break
                
            # Convert from BGR (OpenCV format) to RGB (what Gradio expects)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Yield the frame to Gradio
            yield frame_rgb
            
            # Control frame rate for consistent performance
            # elapsed = time.time() - start_time
            # sleep_time = max(0, 1/FRAME_RATE - elapsed)
            # if sleep_time > 0:
            #     time.sleep(sleep_time)
    
    except Exception as e:
        logger.error(f"Error in webcam feed: {str(e)}")
        raise
    
    finally:
        # Always release resources
        cap.release()
        logger.info("Webcam released")

# Create Gradio interface
demo = gr.Interface(
    fn=webcam_feed,
    inputs=None,  # No inputs needed as we're generating frames
    outputs=gr.Image(label="Webcam Feed"),
    title="Webcam Stream via OpenCV",
    description="Live stream from your webcam using OpenCV's VideoCapture and Gradio",
)

# Launch the application
if __name__ == "__main__":
    logger.info("Starting Gradio application")
    try:
        # Enable share=True to get a public URL for sharing
        demo.launch(share=True)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")