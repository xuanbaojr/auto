from gtts import gTTS
import os
from pydub import AudioSegment
from pydub.effects import speedup

# Xóa các file .mp3 cũ
# for filename in os.listdir('.'):
#     if filename.endswith('.mp3'):
#         os.remove(filename)
#         print(f"Đã xóa file: {filename}")

# Load ting.mp3
ting = AudioSegment.from_file('ting.mp3', format='mp3')
silence = AudioSegment.silent(duration=250)  # 0.5 giây im lặng

# instruction_map = {
#     "1_true": "Xin chào, vui lòng đặt úp bàn tay vào khung",
#     "2_true": "Đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi hở răng",
#     "2_false": "Chưa đạt, đặt lại tay vào khung",
#     "3_true": "Quay sang phải 90 độ",
#     "3_false": "Vui lòng nhìn thẳng camera và cười tươi hở răng",
#     "4_true": "Tiếp tục quay sang phải 90 độ, lưng hướng về camera",
#     "4_false": "Vui lòng quay phải 90 độ so với camera",
#     "5_true": "Tiếp tục quay phải, hướng người về cửa",
#     "5_false": "Chưa đạt, hãy quay lưng về phía camera",
#     "6_true": "Đã hoàn thành, xin cảm ơn",
#     "6_false": "Chưa đạt, vui lòng quay về phía cửa, đầu nhìn thẳng"
# }

# instruction_map = {
#     "1_true": "Xin chào, vui lòng đặt úp bàn tay vào khung",
#     "2_true": "Đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi hở răng",
#     "2_false": "Chưa đạt, đặt lại tay vào khung",
#     "3_true": "Quay người sang phải 90 độ",
#     "3_false": "Vui lòng nhìn thẳng camera và cười tươi hở răng",
#     "4_true": "Tiếp tục quay sang phải 90 độ, lưng hướng về camera",
#     "4_false": "Hãy hướng lưng ra ngoài cửa",
#     "5_true": "Tiếp tục quay phải, hướng người về cửa",
#     "5_false": "Hãy hướng lưng về phía camera",
#     "6_true": "Đã hoàn thành, xin cảm ơn, vui lòng rời khỏi booth",
#     "6_false": "Hãy xoay người về phía cửa"
# }


# instruction_map = {
#     "1_true": "Xin chào, bước 1, vui lòng đặt úp bàn tay vào khung ",
#     "2_true": "Bước 2, đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi hở răng",
#     "2_false": "Bước 1, vui lòng đặt úp bàn tay vào khung",
#     "3_true": "Bước 3, quay người sang phải 90 độ",
#     "3_false": "Bước 2, đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi hở răng",
#     "4_true": "Bước 4, tiếp tục quay sang phải 90 độ, lưng hướng về camera",
#     "4_false": "Bước 3, quay người sang phải 90 độ, lưng hướng về cửa",
#     "5_true": "Bước 5, tiếp tục quay phải, hướng người về cửa",
#     "5_false": "Bước 4, tiếp tục quay sang phải 90 độ, lưng hướng về camera",
#     "6_true": "đã hoàn thành, xin cảm ơn, vui lòng rời khỏi booth",
#     "6_false": "Bước 5, tiếp tục quay phải, hướng người về cửa"
# }

instruction_map = {
    "1_true": "Xin chào. Bước 1: Vui lòng đặt úp bàn tay vào vị trí bên phải.",
    "2_true": "Bước 2: Đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi, hở răng.",
    "2_false": "Bước 1: Vui lòng đặt úp bàn tay vào vị trí bên phải.",
    "3_true": "Bước 3: Quay người sang phải 90 độ.",
    "3_false": "Bước 2: Đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi, hở răng.",
    "4_true": "Bước 4: Tiếp tục quay sang phải 90 độ, lưng hướng về camera.",
    "4_false": "Bước 3: Quay người sang phải 90 độ, lưng hướng ra ngoài.",
    "5_true": "Bước 5: Tiếp tục quay phải, hướng người ra bên ngoài.",
    "5_false": "Bước 4: Tiếp tục quay sang phải 90 độ, lưng hướng về camera.",
    "6_true": "Đã hoàn thành. Xin cảm ơn! Vui lòng rời khỏi booth.",
    "6_false": "Bước 5: Tiếp tục quay phải, hướng người ra bên ngoài."
}


# Tạo file âm thanh
for key, text in instruction_map.items():
    print(f"Đang tạo file cho: {key}")
    
    tts = gTTS(text=text, lang='vi')
    tmp_filename = f"tmp_{key}.mp3"
    tts.save(tmp_filename)
    speech = AudioSegment.from_file(tmp_filename, format='mp3')
    os.remove(tmp_filename)

    if key.endswith('_true'):
        final_audio = ting + silence + speech  # chèn ting + 0.5s trước lời nói
    else:
        final_audio = speech

    output_filename = f"{key}.mp3"
    final_audio.export(output_filename, format='mp3')
    print(f"→ Đã tạo file: {output_filename}")

# Tăng tốc độ phát lại
playback_rate = 1.3

for filename in os.listdir('.'):
    if filename.lower().endswith('.mp3') and not filename.endswith('ting.mp3'):
        print(f"Đang xử lý tăng tốc: {filename}")
        audio = AudioSegment.from_file(filename, format='mp3')
        sped_audio = speedup(audio, playback_speed=playback_rate)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_fast{ext}"
        sped_audio.export(output_filename, format='mp3')
        print(f"→ Đã tạo file tăng tốc: {output_filename}")
        os.remove(filename)

# Đổi tên bỏ hậu tố '_fast'
for filename in os.listdir('.'):
    if filename.lower().endswith('.mp3'):
        os.rename(filename, filename.replace('_fast', ''))
        print(f"Đã đổi tên: {filename} → {filename.replace('_fast', '')}")