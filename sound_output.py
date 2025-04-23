import pygame
import time

class SoundOutput:
    def __init__(self):
        # 1. Khởi tạo pygame mixer
        pygame.mixer.init()
        # 2. Đặt âm lượng mặc định (từ 0.0 tới 1.0)
        pygame.mixer.music.set_volume(1.0)

    def play_sound(self, file_name):
        """
        Phát file âm thanh MP3 đầu vào.
        file_name: đường dẫn tới file .mp3
        """
        try:
            # 3. Nạp file MP3
            pygame.mixer.music.load(file_name)
            # 4. Bắt đầu phát (loop=0 nghĩa không lặp lại)
            pygame.mixer.music.play(loops=0)
            while pygame.mixer.music.get_busy():
                # Dừng 0.1 giây để không chiếm CPU liên tục
                time.sleep(0.1)
        except Exception as e:
            print(f"Lỗi khi phát âm thanh: {e}")


if __name__ == "__main__":
    sound_output = SoundOutput()
    sound_output.play_sound("./sound/5_false.mp3")
