import cv2
import time
import os
from db import DB

class SaveVideo:
    def __init__(self):
        self.db = DB()
        self.is_recording = False
        self.video_writers = [None] * 4
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # mp4v codec
        self.fps = 15
        self.frame_size = (640, 480)
        self.output_dir = 'videos'
        self.recording_start_time = None
        self.current_dir_path = None
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def start_recording(self, rtsp_url1, rtsp_url4, frame1, frame2, frame3, frame4):
        if not self.is_recording:
            # Create timestamp with nested directory structure
            now = time.localtime()
            self.date_folder = time.strftime("%d_%m_%Y", now)
            self.hour = time.strftime("%H", now)
            self.minute = time.strftime("%M", now)
            self.second = time.strftime("%S", now)
            
            # Create nested directory path
            nested_path = os.path.join(self.output_dir, self.date_folder, self.hour, self.minute, self.second)
            os.makedirs(nested_path, exist_ok=True)
            self.current_dir_path = nested_path
            
            # Set file paths using the nested directory structure
            self.video_paths = [
                os.path.join(nested_path, f'cam1.mp4'),
                os.path.join(nested_path, f'cam2.mp4'),
                os.path.join(nested_path, f'cam3.mp4'),
                os.path.join(nested_path, f'cam4.mp4')
            ]
            
            self.frame_size = (frame1.shape[1], frame1.shape[0])
            self.video_writers[0] = cv2.VideoWriter(self.video_paths[0], self.fourcc, self.fps, self.frame_size)
            self.video_writers[1] = cv2.VideoWriter(self.video_paths[1], self.fourcc, self.fps, self.frame_size)
            self.video_writers[2] = cv2.VideoWriter(self.video_paths[2], self.fourcc, self.fps, self.frame_size)
            self.video_writers[3] = cv2.VideoWriter(self.video_paths[3], self.fourcc, self.fps, self.frame_size)
            
            self.recording_start_time = time.time()
            self.is_recording = True
            print("[INFO] Bắt đầu ghi video (.mp4)")
            
        if self.is_recording:
            self.video_writers[0].write(frame1)
            self.video_writers[1].write(frame2)
            self.video_writers[2].write(frame3)
            self.video_writers[3].write(frame4)
    
    def stop_recording(self):
        if self.is_recording:
            # Calculate recording duration
            recording_duration = time.time() - self.recording_start_time
            duration_seconds = int(round(recording_duration))
            
            # Release all video writers
            for writer in self.video_writers:
                if writer is not None:
                    writer.release()
            self.video_writers = [None] * 4
            self.is_recording = False
            
            # Rename directory with duration
            if self.current_dir_path:
                base_dir = os.path.dirname(self.current_dir_path)
                current_dir_name = os.path.basename(self.current_dir_path)
                new_dir_name = f"{current_dir_name}_{duration_seconds}"
                new_dir_path = os.path.join(base_dir, new_dir_name)
                
                # Create new directory and move files
                os.makedirs(new_dir_path, exist_ok=True)
                
                # Move all files from old directory to new directory
                for cam_num in range(1, 5):
                    old_file_path = os.path.join(self.current_dir_path, f'cam{cam_num}.mp4')
                    if os.path.exists(old_file_path):
                        new_file_path = os.path.join(new_dir_path, f'cam{cam_num}.mp4')
                        os.rename(old_file_path, new_file_path)
                
                # Remove old directory if empty
                try:
                    os.rmdir(self.current_dir_path)
                except:
                    pass
                
                self.current_dir_path = None
            
            # Insert data to database
            self.db.insert(self.date_folder, int(self.hour), int(self.minute), int(self.second), duration_seconds) # self.db.insert(self.date_folder, self.hour, self.minute, self.second, duration_seconds)
            print(f"[INFO] Đã dừng ghi video. Thời lượng: {duration_seconds} giây")

        else:
            print("[INFO] Không ghi video")
        
    
    def __del__(self):
        for writer in self.video_writers:
            if writer is not None:
                writer.release()

if __name__ == "__main__":
    save_video = SaveVideo()
    rtsp_url1 = "rtsp://admin:admin@89.207.132.170:554/cam/realmonitor?channel=1&subtype=0"
    rtsp_url4 = "rtsp://admin:admin@89.207.132.170:554/cam/realmonitor?channel=4&subtype=0"
    cap = cv2.VideoCapture(0)
    
    start = time.time()
    while True:
        ret, frame1 = cap.read()
        ret, frame2 = cap.read()
        ret, frame3 = cap.read()
        ret, frame4 = cap.read()
        save_video.start_recording(rtsp_url1, rtsp_url4, frame1, frame2, frame3, frame4)
        
        end = time.time()
        if end - start >= 10:
            save_video.stop_recording()
            break