import subprocess
import time
import os

video_path = "/media/muchomas/rasp_key/1.mp4"

def play_spanned_video(video_path):
    geometry = "7680x2160+0+0"
    command = [
        "/usr/bin/mpv",
        "--fullscreen=yes",
        f"--geometry={geometry}",
        "--loop",
        "--no-osc",
        video_path
    ]
    print(f"Avvio video a schermo intero con geometria: {command}")
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process

if __name__ == "__main__":
    time.sleep(3)
    video_process = play_spanned_video(video_path)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if video_process:
            video_process.terminate()
            video_process.wait()
        print("Processo video terminato.")