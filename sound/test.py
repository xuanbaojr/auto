from gtts import gTTS
# 1. Import lớp gTTS từ thư viện gtts, dùng để tạo đối tượng text-to-speech.

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
# 2. Định nghĩa từ điển chứa cặp key → câu nói tiếng Việt.

for key, text in instruction_map.items():
    """
    3. Duyệt qua từng cặp (key, text) trong instruction_map:
       - key: chuỗi định danh (ví dụ "1_true")
       - text: nội dung câu cần chuyển thành giọng nói
    """
    tts = gTTS(text=text, lang='vi')
    # 4. Tạo đối tượng gTTS với:
    #    - text: chuỗi tiếng Việt
    #    - lang='vi': chỉ định ngôn ngữ là Vietnamese
    #    Thư viện gTTS sẽ gửi yêu cầu đến Google Translate TTS để nhận file âm thanh.

    filename = f"{key}.mp3"
    # 5. Đặt tên file MP3 theo định dạng "<key>.mp3", ví dụ "1_true.mp3".

    tts.save(filename)
    # 6. Lưu file âm thanh ra ổ đĩa với tên đã định.

    print(f"Đã tạo file: {filename}")
    # 7. In thông báo đã tạo thành công file với tên tương ứng.
