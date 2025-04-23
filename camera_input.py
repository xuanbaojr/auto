import cv2
import threading
import queue                # sửa: import module queue
from get_instruction import GetInstruction
from show_video import ShowVideo

class CameraInput:
    def __init__(self, rtsp_url_1, rtsp_url_2, rtsp_url_3, rtsp_url_4):
        self.cap1 = cv2.VideoCapture(rtsp_url_1)
        self.cap2 = cv2.VideoCapture(rtsp_url_2)
        self.cap3 = cv2.VideoCapture(rtsp_url_3)
        self.cap4 = cv2.VideoCapture(rtsp_url_4)

        self.frame_queue = queue.Queue(maxsize=5)
        self.show_video = ShowVideo()
        self.get_instruction = GetInstruction()

        thread = threading.Thread(target=self.instruction_worker, daemon=True)
        thread.start()

    def instruction_worker(self):
        """Luồng phụ: lấy frame từ queue và xử lý instruction."""
        while True:
            frame1, frame2, frame3, frame4 = self.frame_queue.get()
            self.get_instruction.get_instruction(frame1, frame2, frame3, frame4)
            self.frame_queue.task_done()

    def run(self):
        """Luồng chính: đọc frame và hiển thị ngay lập tức."""
        while True:
            ret1, frame1 = self.cap1.read()
            ret2, frame2 = self.cap2.read()
            ret3, frame3 = self.cap3.read()
            ret4, frame4 = self.cap4.read()

            if not ret1:
                break

            self.show_video.show_video(frame1, frame2, frame3, frame4, self.get_instruction.just_checked)
            try:
                self.frame_queue.put_nowait((frame1, frame2, frame3, frame4))
            except queue.Full:    # sửa: catch đúng exception
                pass

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap1.release()
        self.cap2.release()
        self.cap3.release()
        self.cap4.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    from dotenv import load_dotenv
    import os

    load_dotenv()

    rtsp_url_1 = 0
    rtsp_url_2 = os.getenv('RTSP_URL2')
    rtsp_url_3 = os.getenv('RTSP_URL3')
    rtsp_url_4 = os.getenv('RTSP_URL4')
    camera_input = CameraInput(rtsp_url_1, rtsp_url_2, rtsp_url_3, rtsp_url_4)
    camera_input.run()
