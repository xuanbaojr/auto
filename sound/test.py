from gtts import gTTS
import os

# Xóa các file cũ
for filename in os.listdir('.'):
    if filename.endswith('.mp3'):
        os.remove(filename)
        print(f"Đã xóa file: {filename}")

instruction_map = {
    "1_true": "Xin chào, vui lòng đặt up ban tay vao khung",
    "2_true": "đứng vào ô vuông duới chân, nhìn thẳng camera cười như ảnh mau",
    "2_false": "Chưa đạt, dat lai tay vao khung",
    "3_true": "quay người sang phải 90 độ",
    "3_false": "Vui lòng nhìn thẳng camera và cười như ảnh mau",
    "4_true": "quay người sang phải 90 độ",
    "4_false": "Vui lòng quay phải 90 độ so với camera",
    "5_true": "quay người sang phải 90 độ",
    "5_false": "Chưa đạt, hãy quay lưng về phía camera",
    "6_true": "đã hoàn thành, xin cảm ơn",
    "6_false": "Chưa đạt, vui lòng quay người về phía cửa, đầu nhìn thẳng"
}

for key, text in instruction_map.items():
    tts = gTTS(text=text, lang='vi')
    filename = f"{key}.mp3"
    tts.save(filename)
    print(f"Đã tạo file: {filename}")

from pydub import AudioSegment
from pydub.effects import speedup

playback_rate = 1.3

for filename in os.listdir('.'):
    if filename.lower().endswith('.mp3'):
        print(f"Đang xử lý: {filename}")
        audio = AudioSegment.from_file(filename, format='mp3')
        sped_audio = speedup(audio, playback_speed=playback_rate)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_fast{ext}"
        sped_audio.export(output_filename, format='mp3')
        print(f"→ Đã tạo file tăng tốc: {output_filename}")
        os.remove(filename)

for filename in os.listdir('.'):
    if filename.lower().endswith('.mp3'):
        os.rename(filename, filename.replace('_fast', ''))
