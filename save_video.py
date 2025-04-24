import cv2
import numpy as np
import threading
import subprocess
import os
import time
import datetime
import logging
from threading import Event

class SaveVideo:
    """
    Handles multi-camera recording with both FFmpeg (for direct RTSP streams)
    and OpenCV (for frame-by-frame processing) approaches in parallel threads.
    """
    def __init__(self, output_dir="./recordings"):
        # Initialize logging
        self.logger = logging.getLogger('SaveVideo')
        if not self.logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
        # Output directory for recordings
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Recording state tracking
        self.is_recording = False
        self.recording_start_time = 0
        
        # FFmpeg processes
        self.ffmpeg_proc_1 = None
        self.ffmpeg_proc_4 = None
        
        # OpenCV recording objects
        self.cv2_writers = {2: None, 3: None}
        self.cv2_threads = {2: None, 3: None}
        self.cv2_stop_events = {2: Event(), 3: Event()}
        
        # Output file paths
        self.output_paths = {i: None for i in range(1, 5)}
        
        # Track camera properties
        self.camera_properties = {}
        
    def start_recording(self, rtsp_url1, rtsp_url4, frame1, frame2, frame3, frame4):
        """
        Start recording from all cameras.
        
        Args:
            rtsp_url1: RTSP URL for camera 1 (FFmpeg recording)
            rtsp_url4: RTSP URL for camera 4 (FFmpeg recording)
            frame1: First frame from camera 1 (for validation only)
            frame2: First frame from camera 2 (for OpenCV recording)
            frame3: First frame from camera 3 (for OpenCV recording)
            frame4: First frame from camera 4 (for validation only)
        """
        if self.is_recording:
            self.logger.warning("Recording already in progress. Stop first before starting a new one.")
            return
            
        try:
            # Create timestamp-based directory structure for the recordings
            now = datetime.datetime.now()
            date_folder = now.strftime("%d_%m_%Y")
            hour = now.strftime("%H")
            minute = now.strftime("%M")
            second = now.strftime("%S")
            
            # Create nested directory structure
            nested_path = os.path.join(
                self.output_dir, date_folder, hour, minute, second
            )
            os.makedirs(nested_path, exist_ok=True)
            
            # Store initial output paths
            for cam_idx in range(1, 5):
                self.output_paths[cam_idx] = os.path.join(nested_path, f"cam{cam_idx}.mp4")
            
            # Extract frame properties for OpenCV recording
            for cam_idx, frame in [(2, frame2), (3, frame3)]:
                if frame is not None:
                    h, w = frame.shape[:2]
                    self.camera_properties[cam_idx] = {
                        'width': w, 
                        'height': h, 
                        'fps': 30  # Default FPS, could be detected from stream
                    }
                    self.logger.info(f"Camera {cam_idx} properties: {w}x{h} @ 30fps")
            
            # Start FFmpeg threads for cameras 1 and 4
            ffmpeg_thread1 = threading.Thread(
                target=self.ffmpeg_recording, 
                args=(rtsp_url1, 1), 
                name=f"ffmpeg_thread_cam1",
                daemon=True
            )
            
            ffmpeg_thread4 = threading.Thread(
                target=self.ffmpeg_recording, 
                args=(rtsp_url4, 4), 
                name=f"ffmpeg_thread_cam4",
                daemon=True
            )
            
            # Start OpenCV threads for cameras 2 and 3
            # Clear stop events before starting threads
            for cam_idx in [2, 3]:
                self.cv2_stop_events[cam_idx].clear()
            
            cv2_thread2 = threading.Thread(
                target=self.cv2_recording, 
                args=(frame2, 2), 
                name=f"cv2_thread_cam2",
                daemon=True
            )
            
            cv2_thread3 = threading.Thread(
                target=self.cv2_recording, 
                args=(frame3, 3), 
                name=f"cv2_thread_cam3",
                daemon=True
            )
            
            # Store thread references
            self.cv2_threads[2] = cv2_thread2
            self.cv2_threads[3] = cv2_thread3
            
            # Start all threads
            ffmpeg_thread1.start()
            ffmpeg_thread4.start()
            cv2_thread2.start()
            cv2_thread3.start()
            
            # Update recording state
            self.is_recording = True
            self.recording_start_time = time.time()
            self.logger.info("Started recording from all cameras")
            
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            self.stop_recording()  # Cleanup any partial start
    
    def ffmpeg_recording(self, rtsp_url, cam_idx):
        """
        Record from an RTSP stream using FFmpeg.
        
        Args:
            rtsp_url: The RTSP URL to record from
            cam_idx: Camera index (1 or 4)
        """
        try:
            output_path = self.output_paths[cam_idx]
            
            # Configure FFmpeg command for optimal recording
            ffmpeg_cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',       # Use TCP for more reliable streaming
                '-i', rtsp_url,                 # Input RTSP stream
                '-c', 'copy',                   # Copy stream without re-encoding for efficiency
                '-an',                          # Disable audio if not needed
                '-reset_timestamps', '1',       # Reset timestamps for better file compatibility
                '-f', 'mp4',                    # Force MP4 format
                output_path
            ]
            
            self.logger.info(f"Starting FFmpeg recording for camera {cam_idx}")
            
            # Start the FFmpeg process
            proc = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
            
            # Store process reference
            if cam_idx == 1:
                self.ffmpeg_proc_1 = proc
            else:
                self.ffmpeg_proc_4 = proc
                
            # Monitor the process
            while proc.poll() is None:
                if not self.is_recording:
                    # Terminate gracefully by sending 'q' to stdin
                    try:
                        proc.stdin.write(b'q')
                        proc.stdin.flush()
                    except (BrokenPipeError, IOError) as e:
                        self.logger.warning(f"Could not write to FFmpeg stdin for cam{cam_idx}: {e}")
                    
                    # Wait with timeout
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"FFmpeg process for cam{cam_idx} did not terminate gracefully, forcing termination")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            self.logger.error(f"FFmpeg termination failed for cam{cam_idx}, killing process")
                            proc.kill()
                    break
                
                time.sleep(0.5)  # Check periodically without consuming CPU
                
            # Capture and log any errors
            if proc.returncode != 0 and proc.returncode is not None:
                stderr = proc.stderr.read().decode('utf-8', errors='ignore')
                self.logger.error(f"FFmpeg for camera {cam_idx} exited with code {proc.returncode}: {stderr}")
                
        except Exception as e:
            self.logger.error(f"Error in FFmpeg recording thread for camera {cam_idx}: {e}")
        finally:
            # Clear the process reference
            if cam_idx == 1:
                self.ffmpeg_proc_1 = None
            else:
                self.ffmpeg_proc_4 = None
            
            self.logger.info(f"FFmpeg recording thread for camera {cam_idx} ended")
    
    def cv2_recording(self, initial_frame, cam_idx):
        """
        Record frames using OpenCV's VideoWriter.
        
        Args:
            initial_frame: The first frame to record
            cam_idx: Camera index (2 or 3)
        """
        try:
            if initial_frame is None:
                self.logger.error(f"No initial frame provided for camera {cam_idx}, cannot start recording")
                return
                
            # Get output path and properties
            output_path = self.output_paths[cam_idx]
            props = self.camera_properties.get(cam_idx, {})
            
            # Use properties from frame if not already set
            if not props:
                h, w = initial_frame.shape[:2]
                fps = 30  # Default fallback
                self.camera_properties[cam_idx] = {'width': w, 'height': h, 'fps': fps}
                props = self.camera_properties[cam_idx]
            
            # Create VideoWriter with optimal settings
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4 format
            writer = cv2.VideoWriter(
                output_path, 
                fourcc, 
                props['fps'], 
                (props['width'], props['height'])
            )
            
            # Store writer reference
            self.cv2_writers[cam_idx] = writer
            
            # Write the initial frame immediately
            writer.write(initial_frame)
            
            # Track performance metrics
            frames_written = 1
            start_time = time.time()
            last_frame_time = start_time
            dropped_frames = 0
            
            self.logger.info(f"Started OpenCV recording for camera {cam_idx} at {props['fps']} FPS")
            
            # Event for tracking when to stop
            stop_event = self.cv2_stop_events[cam_idx]
            
            while not stop_event.is_set() and self.is_recording:
                # In a real implementation, we'd get new frames here
                # For example:
                # ret, new_frame = camera.get_frame()
                
                # To simulate, we'll just use the initial frame (in real code, we'd get fresh frames)
                new_frame = initial_frame
                
                if new_frame is not None:
                    # Write frame
                    writer.write(new_frame)
                    frames_written += 1
                    
                    # Check timing for frame rate control
                    current_time = time.time()
                    elapsed = current_time - last_frame_time
                    target_interval = 1.0 / props['fps']
                    
                    # Detect dropped frames
                    if elapsed > 1.5 * target_interval:
                        dropped_frames += 1
                        if dropped_frames % 30 == 0:  # Log every 30 dropped frames
                            self.logger.warning(f"Camera {cam_idx} recording may be dropping frames: "
                                               f"{dropped_frames}/{frames_written} frames")
                    
                    # Control FPS by sleeping if needed
                    sleep_time = max(0, target_interval - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    
                    last_frame_time = time.time()
                else:
                    # No frame available
                    time.sleep(0.01)  # Small sleep to prevent CPU spinning
            
            # Calculate actual FPS achieved
            total_time = time.time() - start_time
            actual_fps = frames_written / total_time if total_time > 0 else 0
            
            self.logger.info(f"OpenCV recording for camera {cam_idx} stopped. "
                            f"Recorded {frames_written} frames at {actual_fps:.2f} FPS, "
                            f"dropped approximately {dropped_frames} frames")
            
        except Exception as e:
            self.logger.error(f"Error in OpenCV recording thread for camera {cam_idx}: {e}")
        finally:
            # Clean up resources
            if cam_idx in self.cv2_writers and self.cv2_writers[cam_idx] is not None:
                try:
                    self.cv2_writers[cam_idx].release()
                except Exception as e:
                    self.logger.error(f"Error releasing VideoWriter for camera {cam_idx}: {e}")
                
                self.cv2_writers[cam_idx] = None
            
            self.logger.info(f"OpenCV recording thread for camera {cam_idx} ended")
    
    def stop_recording(self):
        """Stop all recording processes and finalize video files"""
        if not self.is_recording:
            self.logger.info("No recording in progress")
            return
            
        try:
            # Calculate recording duration
            recording_duration = time.time() - self.recording_start_time
            duration_seconds = int(round(recording_duration))
            
            # Set recording flag to False to signal threads to stop
            self.is_recording = False
            
            # Signal all OpenCV threads to stop
            for cam_idx in [2, 3]:
                self.cv2_stop_events[cam_idx].set()
            
            # Stop FFmpeg processes (cameras 1 and 4)
            for cam_idx, proc in [(1, self.ffmpeg_proc_1), (4, self.ffmpeg_proc_4)]:
                if proc is None:
                    continue
                    
                # Send 'q' to FFmpeg stdin for graceful termination
                if proc.stdin:
                    try:
                        proc.stdin.write(b'q')
                        proc.stdin.flush()
                    except (BrokenPipeError, IOError) as e:
                        self.logger.warning(f"Could not write to FFmpeg stdin for cam{cam_idx}: {e}")
                
                # Wait for process to finish with timeout
                try:
                    proc.wait(timeout=10)
                    self.logger.info(f"FFmpeg process stopped for cam{cam_idx}")
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"FFmpeg process for cam{cam_idx} did not terminate gracefully, forcing termination")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.logger.error(f"FFmpeg termination failed for cam{cam_idx}, killing process")
                        proc.kill()
            
            # Wait for OpenCV threads to finish
            for cam_idx in [2, 3]:
                if self.cv2_threads[cam_idx] and self.cv2_threads[cam_idx].is_alive():
                    self.cv2_threads[cam_idx].join(timeout=5.0)
                    if self.cv2_threads[cam_idx].is_alive():
                        self.logger.warning(f"OpenCV thread for camera {cam_idx} did not terminate in time")
                    else:
                        self.logger.info(f"OpenCV thread for camera {cam_idx} stopped")
            
            # Rename directory to include duration
            if any(self.output_paths.values()):
                # Get first valid output path
                for path in self.output_paths.values():
                    if path:
                        # Extract directory components
                        base_dir = os.path.dirname(os.path.dirname(path))  # Go up two levels
                        current_dir_name = os.path.basename(os.path.dirname(path))  # Get the "second" part
                        
                        # Create new directory with duration
                        new_dir_name = f"{current_dir_name}_{duration_seconds}"
                        new_dir_path = os.path.join(base_dir, new_dir_name)
                        
                        # Move the files
                        os.makedirs(new_dir_path, exist_ok=True)
                        
                        # Move all camera files to the new directory
                        for cam_idx in range(1, 5):
                            src_path = self.output_paths.get(cam_idx)
                            if src_path and os.path.exists(src_path):
                                dst_filename = f"cam{cam_idx}.mp4"
                                dst_path = os.path.join(new_dir_path, dst_filename)
                                
                                try:
                                    os.rename(src_path, dst_path)
                                    self.logger.info(f"Moved cam{cam_idx} video to: {dst_path}")
                                    
                                    # Update the path reference
                                    self.output_paths[cam_idx] = dst_path
                                except Exception as e:
                                    self.logger.error(f"Failed to move cam{cam_idx} video: {e}")
                        
                        # Remove the original directory if empty
                        try:
                            original_dir = os.path.dirname(path)
                            if os.path.exists(original_dir) and not os.listdir(original_dir):
                                os.rmdir(original_dir)
                        except Exception as e:
                            self.logger.warning(f"Could not remove original directory: {e}")
                        
                        break  # Only need to process once
            
            self.logger.info(f"All recordings stopped after {recording_duration:.2f} seconds")
        except Exception as e:
            self.logger.error(f"Error stopping recordings: {e}")
        finally:
            # Reset state
            self.is_recording = False
            self.ffmpeg_proc_1 = None
            self.ffmpeg_proc_4 = None
            self.cv2_writers = {2: None, 3: None}
            self.cv2_threads = {2: None, 3: None}

if __name__ == "__main__":
    recorder = SaveVideo()
    rtsp_urls = {
        1: "rtsp://admin:admin@192.168.1.64:554/cam/realmonitor?channel=1&subtype=0",
        2: "rtsp://admin:admin@192.168.1.65:554/cam/realmonitor?channel=1&subtype=0",
        3: "rtsp://admin:admin@192.168.1.66:554/cam/realmonitor?channel=1&subtype=0",
        4: "rtsp://admin:admin@192.168.1.67:554/cam/realmonitor?channel=1&subtype=0"
    }

    recorder.start_recording()
    time.sleep(10)  # Record for 10 seconds
    recorder.stop_recording()
