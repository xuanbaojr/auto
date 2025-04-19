from service.booth_check import BoothCheck

class AttendantCheck:
    def __init__(self):
        self.booth_check = BoothCheck()
    
    def is_attendant_in_booth(self, frame):
        return self.booth_check.check(frame)