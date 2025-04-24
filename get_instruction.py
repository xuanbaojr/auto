from attendant_check import AttendantCheck
from sound_output import SoundOutput
import time

instruction_map = {
    "1_true": "Xin chào, vui lòng đặt các ngón tay lên hai miếng dán bên phải",
    "2_true": "Tốt, bỏ tay khỏi vị trí đang đặt, đứng vào ô vuông duới chân, nhìn thẳng camera",
    "2_false": "Chưa đạt, vui lòng đặt tay lên giá theo hướng dẫn",
    "3_true": "Tốt, hãy nhìn bốn hướng theo video huớng dẫn",
    "3_false": "Chưa đạt, Vui lòng đứng vào ô vuông duới chân, nhìn thẳng camera",
    # bat dau nhin len
    "4_true": "Tốt",              # check nhin len
    "4_false": "Vui lòng nhìn ngưóc lên như hướng dẫn",
    "5_true": "Tốt, hãy nhìn thẳng camera và cười như ảnh hướng dẫn",    # check nhin sang trai
    "5_false": "Hãy nhìn sang trái như ảnh hướng dẫn",

    "6_true": "Tốt, quay người sang phải 90 độ, giữ thẳng người, đầu nhìn thẳng",
    "6_false": "Vui lòng nhìn thẳng camera và cười như ảnh hướng dẫn",
    "7_true": "Tốt, vui long quay lưng về phía camera, giữ thẳng người, đầu nhìn thẳng",
    "7_false": "Vui lòng quay phải 90 độ so với camera",
    "8_true": "Tốt, vui lòng quay người sang phải 90 độ, đầu nhìn thẳng về phía cửa",
    "8_false": "Chưa đạt, hãy quay lưng về phía camera, đầu nhìn thẳng",
    "9_true": "Tốt, đã hoàn thành, xin cảm ơn",
    "9_false": "Chưa đạt, vui lòng quay người về phía cửa, đầu nhìn thẳng"
}

class GetInstruction:
    def __init__(self):
        self.just_checked = 0
        self.false_num = 0
        self.true_frames = 0
        self.false_frames = 0

        self.true_frames_max = 2
        self.false_frames_max = 30
        self.false_num_max =  3
        self.attendant_check = AttendantCheck()
        self.sound_output = SoundOutput()

    def start_get_instruction(self, frame1, frame2, frame3, frame4):
        checked_result = self.attendant_check.check(frame1, frame2, frame3, frame4, self.just_checked)
        if self.just_checked != 0:
            if checked_result == False:
               
                if self.false_num == self.false_num_max:
                    self.just_checked += 1
                    self.show_instruction(f"{self.just_checked}_true", True)

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
