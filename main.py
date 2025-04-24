import cv2
import numpy as np
import threading
import queue
import time
from threading import Lock
from get_instruction import GetInstruction
from attendant_check import AttendantCheck

class ThreadedCamera:
    """Reads frames from an RTSP stream in a background thread to avoid blocking."""
    def __init__(self, rtsp_url, name="Camera"):
        self.rtsp_url = rtsp_url
        self.name = name
        self.lock = Lock()
        self.running = True
        self.last_frame = None
        self.last_ready = False

        self._thread = threading.Thread(target=self._buffer_frames, daemon=True)
        self._thread.start()

    def _buffer_frames(self):
        cap = cv2.VideoCapture(self.rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('H', '2', '6', '4'))
        last_reconnect = 0

        while self.running:
            ret, frame = cap.read()
            with self.lock:
                self.last_ready = ret
                if ret:
                    self.last_frame = frame
                else:
                    now = time.time()
                    if now - last_reconnect > 3:
                        cap.release()
                        cap = cv2.VideoCapture(self.rtsp_url)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('H', '2', '6', '4'))
                        last_reconnect = now
            time.sleep(0.01)
        cap.release()

    def get_frame(self):
        """Returns the most recent frame (ret, frame)."""
        with self.lock:
            if self.last_ready and self.last_frame is not None:
                return True, self.last_frame.copy()
            else:
                return False, None

    def release(self):
        self.running = False
        self._thread.join(timeout=1.0)


class CameraInput:
    def __init__(self, rtsp_urls):
        # Initialize four threaded cameras
        self.cams = [ThreadedCamera(url, f"Cam{i+1}") for i, url in enumerate(rtsp_urls)]
        self.frame_queue = queue.Queue(maxsize=5)
        self.get_instruction = GetInstruction()
        self.attendant_check = AttendantCheck()
        self.is_check_booth = False
        self.num_frames_false = 0
        self.num_frames_false_max = 20

        self.check_booth = threading.Thread(target=self._check_booth_worker, daemon=True)
        self.check_booth.start()

        self.get_instruction_worker = threading.Thread(target=self._get_instruction_worker, daemon=True)
        self.get_instruction_worker.start()
    
    def _check_booth_worker(self):
        while True:
            frames = self.frame_queue.get()
            checked_result =self.attendant_check.check(*frames, 0)
            if checked_result:
                self.is_check_booth = True
                self.num_frames_false = 0
            else:
                self.num_frames_false += 1
                if self.num_frames_false > self.num_frames_false_max:
                    self.is_check_booth = False
                    self.num_frames_false = 0
            self.frame_queue.task_done()
        
    def _get_instruction_worker(self):
        while True:
            frames = self.frame_queue.get()
            if self.is_check_booth == True and self.get_instruction.get_just_checked() != 9:
                self.get_instruction.start_get_instruction(*frames)
            if self.is_check_booth == False:
                self.get_instruction.stop_get_instruction()
            self.frame_queue.task_done()

    def run(self):
        from show_video import ShowVideo
        show = ShowVideo()

        try:
            while True:
                results = [cam.get_frame() for cam in self.cams]
                rets, frames = zip(*results)
                show.show_video(*frames, self.get_instruction.just_checked)
                try:
                    self.frame_queue.put_nowait(frames)
                except queue.Full:
                    pass
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        finally:
            # Cleanup
            for cam in self.cams:
                cam.release()
            cv2.destroyAllWindows()


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()

    urls = [os.getenv(f'RTSP_URL{i+1}') for i in range(4)]
    app = CameraInput(urls)
    app.run()
