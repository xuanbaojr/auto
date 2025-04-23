import psutil
import time

while True:
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    current_time = time.localtime()
    print(f"CPU: {cpu}% | RAM: {ram}% | Time: {current_time.tm_hour:02d}:{current_time.tm_min:02d}:{current_time.tm_sec:02d}")