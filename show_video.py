import cv2
import numpy as np

class ShowVideo:
    def __init__(self):
        self.render_frame = np.zeros((768, 1366, 3), dtype=np.uint8)
        self.frame = None
    def show_video(self, frame1, frame2, frame3, frame4, just_checked):
        frame1 = cv2.resize(frame1, (1366//2, 768//2))
        cv2.putText(frame1, f"{just_checked}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        frame4 = cv2.resize(frame1, (1366//2, 768//2))

        if just_checked == 0:
            img_instruction = cv2.resize(cv2.imread("./ims_instruction/1.png"), (1366//2, 768))
            self.render_frame[0:768, 1366//2:1366] = img_instruction
        elif just_checked == 3:
            img_instruction = cv2.resize(cv2.imread("./ims_instruction/2.png"), (1366//2, 768))
            self.render_frame[0:768, 1366//2:1366] = img_instruction
        elif just_checked == 4:
            img_instruction = cv2.resize(cv2.imread("./ims_instruction/3.png"), (1366//2, 768))
            self.render_frame[0:768, 1366//2:1366] = img_instruction
        elif just_checked == 5:
            img_instruction = cv2.resize(cv2.imread("./ims_instruction/4.png"), (1366//2, 768))
            self.render_frame[0:768, 1366//2:1366] = img_instruction
        elif just_checked == 6:
            img_instruction = cv2.resize(cv2.imread("./ims_instruction/5.png"), (1366//2, 768))
            self.render_frame[0:768, 1366//2:1366] = img_instruction
        elif just_checked == 7:
            img_instruction = cv2.resize(cv2.imread("./ims_instruction/6.png"), (1366//2, 768))
            self.render_frame[0:768, 1366//2:1366] = img_instruction
        elif just_checked == 8:
            img_instruction = cv2.resize(cv2.imread("./ims_instruction/7.png"), (1366//2, 768))
            self.render_frame[0:768, 1366//2:1366] = img_instruction
        elif just_checked == 9:
            img_instruction = cv2.resize(cv2.imread("./ims_instruction/8.png"), (1366//2, 768))
            self.render_frame[0:768, 1366//2:1366] = img_instruction
        elif just_checked == 10:
            img_instruction = cv2.resize(cv2.imread("./ims_instruction/9.png"), (1366//2, 768))
            self.render_frame[0:768, 1366//2:1366] = img_instruction

        self.render_frame[0:768//2, 0:1366//2] = frame1
        self.render_frame[768//2:768, 0:1366//2] = frame4
        cv2.imshow('Camera 1', self.render_frame)
        cv2.waitKey(1)