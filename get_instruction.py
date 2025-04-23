from attendant_check import AttendantCheck
from sound_output import SoundOutput

instruction_map = {
    1: "Xin chao, vui long dat tay len gia quet.",
    2: "Vui long tro ve vi tri ban dau va nhin thang vao camera.",
    3: "He thong bat dau quet khuon mat. Tiep vien nhin ngang len phia tren khoang 45 do",
    4: "Nhin phai khoang 45 do.",
    5: "Nhin xuong khoang 45 do.",
    6: "Nhin trai khoang 45 do.",
    7: "Vui long nhin thang vao camera va cuoi tuoi.",
    8: "Quay sang phai 90 do va giu nguoi thang.",
    9: "Tot. Tiep tuc quay sang phai 90 do va giu nguoi thang.",
    10: "Tot. Tiep tuc quay sang phai 90 do va giu nguoi thang.",
    11: "Quy trinh da hoan tat. Xin cam on"
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
                self.show_instruction(instruction_map[self.just_checked])
                self.just_checked = 0

            
    def show_instruction(self, instruction_str):
        self.sound_output.play_sound(instruction_str)