import pygame
import time
import threading
from collections import deque

class SoundOutput:
    def __init__(self):
        # 1. Khởi tạo bộ phát của pygame để xử lý âm thanh
        pygame.mixer.init()
        # 2. Đặt âm lượng mặc định (giá trị từ 0.0 đến 1.0)
        pygame.mixer.music.set_volume(1.0)

        # 3. Tạo hàng đợi để lưu các yêu cầu phát âm thanh (file_name, is_to_true)
        self.queue = deque()
        # 4. Lock để đồng bộ giữa các luồng khi truy cập queue và cờ interrupt
        self.lock = threading.Lock()
        # 5. Cờ báo luồng phát nhạc đang phải dừng ngay (khi có file true mới)
        self.interrupt = False

        # 6. Khởi động luồng nền xử lý phát nhạc liên tục
        t = threading.Thread(target=self._player_thread, daemon=True)
        t.start()

    def play_sound(self, file_name, is_to_true=False):
        """
        Đưa lệnh phát âm thanh vào queue.
        Nếu is_to_true=True sẽ:
          - Giữ lại chỉ các yêu cầu true trong queue
          - Đưa yêu cầu mới lên đầu queue
          - Gọi cờ interrupt để dừng ngay luồng đang phát
        """
        with self.lock:
            if is_to_true:
                # 7.1 Lọc lại queue chỉ giữ các yêu cầu đã đánh dấu true (nếu có)
                self.queue = deque([item for item in self.queue if item[1]])
                # 7.2 Đưa file true mới lên đầu queue để phát ngay
                self.queue.appendleft((file_name, is_to_true))
                # 7.3 Đặt cờ dừng luồng phát hiện tại ngay
                self.interrupt = True
            else:
                # 7.4 Thêm file bình thường (false) vào cuối queue
                self.queue.append((file_name, is_to_true))

    def _player_thread(self):
        """
        Luồng nền:
          - Liên tục lấy lệnh từ queue
          - Phát file, kiểm tra interrupt để có thể dừng ngay
        """
        while True:
            item = None
            with self.lock:
                if self.queue:
                    # 8.1 Lấy phần tử đầu queue (FIFO)
                    item = self.queue.popleft()
                    # 8.2 Reset cờ interrupt trước khi phát file mới
                    self.interrupt = False

            if item is None:
                # 8.3 Nếu queue rỗng, nghỉ 0.1s tránh busy-wait
                time.sleep(0.1)
                continue

            file_name, is_true = item
            try:
                # 9. Nạp file mp3 từ thư mục sound
                pygame.mixer.music.load(f"./sound/{file_name}.mp3")
                # 10. Phát file, không lặp lại
                pygame.mixer.music.play(loops=0)

                # 11. Kiểm tra trong khi phát nếu có interrupt thì dừng ngay
                while pygame.mixer.music.get_busy():
                    with self.lock:
                        if self.interrupt:
                            pygame.mixer.music.stop()
                            break
                    time.sleep(0.1)

            except Exception as e:
                # 12. In lỗi nếu không load hoặc phát được file
                print(f"Lỗi khi phát âm thanh '{file_name}': {e}")
