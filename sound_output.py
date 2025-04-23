import cv2
import numpy as np

class SoundOutput:
    def __init__(self, window_name='Sound Output', width=1500, height=100):
        # Lưu tên cửa sổ để sử dụng khi hiển thị
        self.window_name = window_name
        # Tạo cửa sổ với kích thước tự động thích ứng nội dung
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        # Lưu kích thước khung hình (pixel)
        self.width = width
        self.height = height

    def play_sound(self, sound):
        # 1. Tạo một ảnh nền trắng kích thước height x width, 3 kênh màu, datatype uint8
        img = np.ones((self.height, self.width, 3), dtype=np.uint8) * 255

        # 2. Chọn font chữ của OpenCV
        font = cv2.FONT_HERSHEY_SIMPLEX

        # 3. Viết chuỗi sound lên ảnh tại vị trí (10, height//2)
        #    - str(sound): đảm bảo sound là chuỗi
        #    - font: font đã chọn
        #    - fontScale=1: tỉ lệ phóng to/thu nhỏ chữ
        #    - color=(0,0,0): màu chữ đen (B, G, R)
        #    - thickness=2: độ dày của nét chữ
        #    - lineType=cv2.LINE_AA: loại đường vẽ, LINE_AA cho chất lượng khử răng cưa tốt
        cv2.putText(img, str(sound),
                    (10, self.height // 2),
                    font,
                    1,
                    (0, 0, 0),
                    2,
                    cv2.LINE_AA)

        # 4. Hiển thị ảnh vừa vẽ chữ lên cửa sổ đã tạo
        cv2.imshow(self.window_name, img)

        # 5. Gọi cv2.waitKey(1) để OpenCV cập nhật cửa sổ; 
        #    nếu bỏ qua, cửa sổ sẽ không render. Giá trị 1 ms đủ để không chặn luồng chính.
        cv2.waitKey(1)
