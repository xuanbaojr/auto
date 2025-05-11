import cv2
import time
import numpy as np
import asyncio

class ShowVideo:
    def __init__(self):
        self.render_frame = np.zeros((768, 1366, 3), dtype=np.uint8)
        self.frame = None
        self.im_0 = cv2.resize(cv2.imread("./ims_instruction/1.png"), (1366//2, 768))
        self.im_1 = cv2.resize(cv2.imread("./ims_instruction/2.png"), (1366//2, 768))
        self.im_2 = cv2.resize(cv2.imread("./ims_instruction/3.png"), (1366//2, 768))   
        self.faceid = [ cv2.resize(cv2.imread("./ims_instruction/4.png"), (1366//2, 768)),
                        cv2.resize(cv2.imread("./ims_instruction/5.png"), (1366//2, 768)),
                        cv2.resize(cv2.imread("./ims_instruction/6.png"), (1366//2, 768)),
                        cv2.resize(cv2.imread("./ims_instruction/7.png"), (1366//2, 768))]
        self.faceid_idx = 0
        self.im_4 = cv2.resize(cv2.imread("./ims_instruction/8.png"), (1366//2, 768))
        self.im_5 = cv2.resize(cv2.imread("./ims_instruction/9.png"), (1366//2, 768))
        self.im_6 = cv2.resize(cv2.imread("./ims_instruction/10.png"), (1366//2, 768))
        self.im_7 = cv2.resize(cv2.imread("./ims_instruction/11.png"), (1366//2, 768))

    def show_video(self, frame1, frame2, frame3, frame4, just_checked):
        if just_checked == 0:
            just_checked = "READY"
        frame1 = cv2.resize(frame1, (1366//2, 768//2))
        frame3 = cv2.resize(frame3, (1366//2, 768//2))
        cv2.putText(frame1, f"{just_checked}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        frame4 = cv2.resize(frame4, (1366//2, 768//2))

        if just_checked == "READY":
            self.render_frame[0:768, 1366//2:1366] = self.im_0
        elif just_checked == 1:
            self.render_frame[0:768, 1366//2:1366] = self.im_1
        elif just_checked == 2:
            self.render_frame[0:768, 1366//2:1366] = self.im_4
        elif just_checked == 3:
            self.render_frame[0:768, 1366//2:1366] = self.im_5
        elif just_checked == 4:
            self.render_frame[0:768, 1366//2:1366] = self.im_6
        elif just_checked == 5:
            self.render_frame[0:768, 1366//2:1366] = self.im_7
        elif just_checked == 6:           # xoay xong faceid
            self.render_frame[0:768, 1366//2:1366] = self.im_0
        self.render_frame[0:768//2, 0:1366//2] = frame1
        if just_checked == 2:
            self.render_frame[768//2:768, 0:1366//2] = frame3
        else:
            self.render_frame[768//2:768, 0:1366//2] = frame4
        cv2.imshow('Camera 1', self.render_frame)
        cv2.waitKey(1)