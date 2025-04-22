from attendant_check import AttendantCheck
from sound_output import SoundOutput

instruction_map = {
    1: "Xin chào, vui lòng đặt tay lên giá quét.",
    2: "Quét bàn tay hoàn tất. Tiếp viên vui lòng trở về vị trí ban đầu và nhìn thẳng vào camera.",
    3: "Hệ thống bắt đầu quét khuôn mặt. Tiếp viên ngẩng nhìn lên phía trên khoảng 45 độ",
    4: "Nhìn sang phải khoảng 45 độ.",
    5: "Nhìn xuống khoảng 45 độ.",
    6: "Nhìn sang trái khoảng 45 độ.",
    7: "Vui lòng nhìn thẳng vào camera và cười tươi.",
    8: "Quay sang phải 90 độ và giữ người thẳng.",
    9: "Tốt. Tiếp tục quay sang phải 90 độ và giữ người thẳng.",
    10: "Tốt. Tiếp tục quay sang phải 90 độ và giữ người thẳng.",
    11: "Quy trình đã hoàn tất. Xin cảm ơn"
}

class GetInstruction:
    def __init__(self):
        self.just_checked = 0
        self.attendant_check = AttendantCheck()
        self.sound_output = SoundOutput()

    def get_instruction(self, frame1, frame2, frame3, frame4):
        checked_result = self.attendant_check.check(frame1, frame2, frame3, frame4, self.just_checked)
        if checked_result == True:
            self.just_checked += 1
            self.show_instruction(instruction_map[self.just_checked])
            if self.just_checked == 11:
                self.just_checked = 0

            
    def show_instruction(self, instruction_str):
        self.sound_output.play_sound(instruction_str)