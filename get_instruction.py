from attendant_check import AttendantCheck
from sound_output import SoundOutput
import time


instruction_map = {
    "1_true": "Xin chào, bước 1, vui lòng đặt úp bàn tay vào khung",
    "2_true": "Bước 2, đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi hở răng",
    "2_false": "Bước 1, vui lòng đặt úp bàn tay vào khung",
    "3_true": "Bước 3, quay người sang phải 90 độ",
    "3_false": "Bước 2, đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi hở răng",
    "4_true": "Bước 4, tiếp tục quay sang phải 90 độ, lưng hướng về camera",
    "4_false": "Bước 3, quay người sang phải 90 độ",
    "5_true": "Bước 5, tiếp tục quay phải, hướng người về cửa",
    "5_false": "Bước 4, tiếp tục quay sang phải 90 độ, lưng hướng về camera",
    "6_true": "Bước 6, đã hoàn thành, xin cảm ơn, vui lòng rời khỏi booth",
    "6_false": "Bước 5, tiếp tục quay phải, hướng người về cửa"
}

class GetInstruction:
    def __init__(self):
        self.just_checked = 0
        self.false_num = 0
        self.true_frames = 0
        self.false_frames = 0

        self.true_frames_max = 1
        self.false_frames_max = 12
        self.false_num_max =  3
        self.attendant_check = AttendantCheck()
        self.sound_output = SoundOutput()

    def start_get_instruction(self, frame1, frame2, frame3, frame4):
        if self.just_checked == 0:
            self.just_checked = 1
            self.show_instruction("1_true", True)
            return

        if self.just_checked != 0:
            checked_result = self.attendant_check.check(frame1, frame2, frame3, frame4, self.just_checked)
            if checked_result == False:
               
                if self.false_num == self.false_num_max:
                    self.just_checked += 1
                    self.show_instruction(f"{self.just_checked}_true", True)
                    self.false_num = 0
                    self.true_frames = 0
                    self.false_frames = 0

                else:
                    self.false_frames += 1
                    if self.false_frames == self.false_frames_max:
                        self.false_num += 1
                        self.show_instruction(f"{self.just_checked+1}_false")
                        self.false_frames = 0
                        self.true_frames = 0

            if checked_result == True:
                self.true_frames += 1
                if self.true_frames == self.true_frames_max:
                    self.just_checked += 1
                    self.show_instruction(f"{self.just_checked}_true", True) 
                    self.false_num = 0
                    self.true_frames = 0
                    self.false_frames = 0
             

    def stop_get_instruction(self):
        self.sound_output.stop_sound()
        self.just_checked = 0
        self.false_num = 0
        self.true_frames = 0
        self.false_frames = 0

    def show_instruction(self, instruction_str, is_to_true=False):
        self.sound_output.play_sound(instruction_str, is_to_true)

    def get_just_checked(self):
        return self.just_checked
