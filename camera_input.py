import cv2
from get_instruction import GetInstruction

class CameraInput:
    def __init__(self, rtsp_url_1, rtsp_url_2, rtsp_url_3, rtsp_url_4):
        self.cap1 = cv2.VideoCapture(rtsp_url_1)
        self.cap2 = cv2.VideoCapture(rtsp_url_2)
        self.cap3 = cv2.VideoCapture(rtsp_url_3)
        self.cap4 = cv2.VideoCapture(rtsp_url_4)
        self.get_instruction = GetInstruction()

    def run(self):
        while True:
            ret1, frame1 = self.cap1.read()
            ret2, frame2 = self.cap2.read()
            ret3, frame3 = self.cap3.read()
            ret4, frame4 = self.cap4.read()

            if ret1 and ret2 and ret3 and ret4:
                # self.show_video(frame1, frame2, frame3, frame4)
                self.send_input(frame1, frame2, frame3, frame4)
        
    def show_video(self, frame1, frame2, frame3, frame4):
        cv2.imshow('Camera 1', frame1)
        # cv2.imshow('Camera 2', frame2)
        # cv2.imshow('Camera 3', frame3)
        # cv2.imshow('Camera 4', frame4)
        cv2.waitKey(1)
    
    def send_input(self, frame1, frame2, frame3, frame4):
        self.get_instruction.get_instruction(frame1, frame2, frame3, frame4)


if __name__ == '__main__':
    from dotenv import load_dotenv
    import os

    load_dotenv()

    rtsp_url_1 = os.getenv('RTSP_URL1')
    rtsp_url_2 = os.getenv('RTSP_URL2')
    rtsp_url_3 = os.getenv('RTSP_URL3')
    rtsp_url_4 = os.getenv('RTSP_URL4')
    camera_input = CameraInput(rtsp_url_1, rtsp_url_2, rtsp_url_3, rtsp_url_4)
    camera_input.run()