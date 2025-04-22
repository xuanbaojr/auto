import os
import numpy as np
import tensorflow as tf
import cv2

class FaceInfo:
    def __init__(self, model_dir=None, image_shape_max=640):
        self.current_dir = os.path.dirname(os.path.realpath(__file__))
        self.model_dir = model_dir or os.path.join(self.current_dir, 'tf_retinaface_mbv2')
        self.detector_model = tf.saved_model.load(self.model_dir)
        self.image_shape_max = image_shape_max

    def get_face_info(self, frame):
        """
        Tham số:
            frame (ndarray): ảnh BGR đầu vào (OpenCV)
        Trả về:
            pitch (float), roll (float), yaw (float), smile_ratio (float)
            hoặc (None, None, None, None) nếu không phát hiện được khuôn mặt
        """
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        landmarks, bboxes, scores = self._detect_faces(image_rgb)
        if len(bboxes) == 0:
            return None, None, None, None

        lmarks = np.transpose(landmarks)
        bb, pts5 = self._one_face(image_rgb, bboxes, lmarks)
        if not self._are_coordinates_in_frame(image_rgb, bb, pts5):
            return None, None, None, None

        roll   = self._find_roll(pts5)
        yaw    = self._find_yaw(pts5)
        pitch  = self._find_pitch(pts5)
        smile  = self._find_smile(pts5)

        return pitch, roll, yaw, smile

    def _detect_faces(self, image):
        """Resize ảnh nếu cần và gọi RetinaFace để lấy bboxes, landmarks."""
        h, w = image.shape[:2]
        scale = max(1, max(h, w) / self.image_shape_max)
        if scale > 1:
            small = cv2.resize(image, None, fx=1/scale, fy=1/scale)
            bbs_all, pts_all = self._retinaface(small)
            bbs_all[:, :4] *= scale
            pts_all  *= scale
        else:
            bbs_all, pts_all = self._retinaface(image)
        scores = bbs_all[:, 4]
        bboxes = bbs_all[:, :4]
        return pts_all, bboxes, scores

    def _retinaface(self, img):
        """Chạy inference RetinaFace và chuyển kết quả về kích thước gốc."""
        h, w = img.shape[:2]
        img_pad, pad = self._pad_input_image(img)
        inp = tf.convert_to_tensor(img_pad[np.newaxis, ...], tf.float32)
        outputs = self.detector_model(inp).numpy()
        outputs = self._recover_pad_output(outputs, pad)

        n = len(outputs)
        bbs = np.zeros((n,5), dtype=np.float32)
        lms = np.zeros((n,10), dtype=np.float32)
        bbs[:, [0,2]] = outputs[:, [0,2]] * w
        bbs[:, [1,3]] = outputs[:, [1,3]] * h
        bbs[:, 4]      = outputs[:, -1]
        lms[:, 0:5]   = outputs[:, [4,6,8,10,12]] * w
        lms[:, 5:10]  = outputs[:, [5,7,9,11,13]] * h
        return bbs, lms

    def _pad_input_image(self, img, max_steps=32):
        """Đệm ảnh để chiều cao, rộng chia hết cho max_steps."""
        h, w, _ = img.shape
        pad_h = (max_steps - h % max_steps) if h % max_steps else 0
        pad_w = (max_steps - w % max_steps) if w % max_steps else 0
        val = np.mean(img, axis=(0,1)).astype(np.uint8).tolist()
        img_pad = cv2.copyMakeBorder(img, 0, pad_h, 0, pad_w,
                                     cv2.BORDER_CONSTANT, value=val)
        return img_pad, (h, w, pad_h, pad_w)

    def _recover_pad_output(self, outputs, pad):
        """Điều chỉnh lại tọa độ sau khi đã padding."""
        h, w, ph, pw = pad
        scale_x = (w + pw) / w
        scale_y = (h + ph) / h
        coords = outputs[:, :14].reshape(-1,7,2)
        coords *= [scale_x, scale_y]
        outputs[:, :14] = coords.reshape(-1,14)
        return outputs

    def _one_face(self, frame, bbs, pts):
        """Chọn mặt gần tâm khung ảnh nhất."""
        # Tâm của mỗi bbox so với tâm ảnh
        cx = (bbs[:,0] + bbs[:,2]) / 2 - frame.shape[1]/2
        cy = (bbs[:,1] + bbs[:,3]) / 2 - frame.shape[0]/2
        dist = np.abs(cx) + np.abs(cy)
        idx  = np.argmin(dist)
        return bbs[idx], pts[:, idx]

    def _are_coordinates_in_frame(self, frame, box, pts):
        """Kiểm tra bbox và landmarks có nằm trong ảnh không."""
        h, w = frame.shape[:2]
        if np.any(box < 0) or box[2] > w or box[3] > h:
            return False
        if np.any(pts < 0) or np.max(pts[0:5]) > w or np.max(pts[5:10]) > h:
            return False
        return True

    def _find_smile(self, pts):
        """Tính tỉ lệ khoảng cách miệng so với khoảng cách hai mắt."""
        dx_eye = pts[1] - pts[0]
        dx_mou = pts[4] - pts[3]
        return dx_mou / dx_eye

    def _find_roll(self, pts):
        """Chênh lệch y giữa hai mắt -> roll."""
        return pts[6] - pts[5]

    def _find_yaw(self, pts):
        """Hiệu khoảng cách ngang từ mũi tới mắt trái/trái tới mắt phải."""
        le2n = pts[2] - pts[0]
        re2n = pts[1] - pts[2]
        return le2n - re2n

    def _find_pitch(self, pts):
        """Tỉ lệ khoảng cách mắt-mũi so với mũi-miệng -> pitch."""
        eye_y = (pts[5] + pts[6]) / 2
        mou_y = (pts[8] + pts[9]) / 2
        return (eye_y - pts[7]) / (pts[7] - mou_y)

if __name__ == '__main__':
    face_info = FaceInfo()
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        pitch, roll, yaw, smile = face_info.get_face_info(frame)
        print(pitch, roll, yaw, smile)
        cv2.imshow('frame', frame)
        if cv2.waitKey(1) == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
