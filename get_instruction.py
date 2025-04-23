from attendant_check import AttendantCheck
from sound_output import SoundOutput

instruction_map = {
    "1_true": "Xin chào, vui lòng đặt tay lên giá theo hướng dẫn",
    "2_true": "Tốt, quay về ô vuông, xem video hướng dẫn, nhìn thẳng camera và nhìn lần lượt 4 hướng",
    "2_false": "Chưa đạt, vui lòng đặt tay lên giá theo hướng dẫn",
    "3_true": "Tốt, hãy nhìn lên trên như video hướng dẫn",
    "3_false": "Vui lòng nhìn thẳng vào camera",
    "4_true": "Tốt",
    "4_false": "Hãy nhìn lên trên như video hướng dẫn",
    "5_true": "Tốt",
    "5_false": "Hãy nhìn sang phải như video hướng dẫn",
    "6_true": "Tốt",
    "6_false": "Hãy nhìn xuống dưới như video hướng dẫn",
    "7_true": "Tốt, hãy nhìn thẳng camera và cười như ảnh hướng dẫn",
    "7_false": "Hãy nhìn sang trái như video hướng dẫn",
    "8_true": "Tốt, quay phải 90 độ, giữ thẳng người, đầu nhìn thẳng",
    "8_false": "Vui lòng nhìn thẳng camera và cười như ảnh hướng dẫn",
    "9_true": "Tốt, quay phải quay lưng về phía camera, giữ thẳng người, đầu nhìn thẳng",
    "9_false": "Vui lòng quay phải 90 độ so với camera",
    "10_true": "Tốt, quay phải 90 độ, đầu nhìn thẳng về phía cửa",
    "10_false": "Chưa đạt, hãy quay lưng về phía camera, đầu nhìn thẳng",
    "11_true": "Tốt, đã hoàn thành, xin cảm ơn",
    "11_false": "Chưa đạt, vui lòng quay người về phía cửa, đầu nhìn thẳng"
}

class GetInstruction:
    def __init__(self):
        self.just_checked = 0
        self.false_num = 0
        self.true_frames = 0
        self.false_frames = 0

        self.true_frames_max = 2
        self.false_frames_max = 200
        self.false_num_max =  3
        self.attendant_check = AttendantCheck()
        self.sound_output = SoundOutput()

    def get_instruction(self, frame1, frame2, frame3, frame4):
        checked_result = self.attendant_check.check(frame1, frame2, frame3, frame4, self.just_checked)
        if self.just_checked != 0:
            if checked_result == False:
               
                if self.false_num == self.false_num_max:
                    self.just_checked += 1
                    self.show_instruction(f"{self.just_checked}_true", True)

                    if self.just_checked == 11:
                        self.just_checked = 0
                    self.false_num = 0
                    self.false_frames = 0
                    self.true_frames = 0
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
                if self.just_checked == 11:
                    self.just_checked = 0
                self.true_frames = 0
                self.false_num = 0
                self.false_frames = 0                   

            
    def show_instruction(self, instruction_str, is_to_true=False):
        self.sound_output.play_sound(instruction_str, is_to_true)
