import subprocess
import time
import os

video1_path = "/media/muchomas/rasp_key/1.mp4"
video2_path = "/media/muchomas/rasp_key/2.mp4"

def play_video_on_screen(video_path, screen_number):
    command = [
        "/usr/bin/mpv",
        "--fullscreen=yes",
        f"--screen={screen_number}",
        "--loop",
        "--no-osc",
        video_path
    ]
    print(f"Avvio su schermo {screen_number}: {command}")
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process

if __name__ == "__main__":
    time.sleep(5)

    process2 = play_video_on_screen(video2_path, 1)
    time.sleep(0.5)
    process1 = play_video_on_screen(video1_path, 0)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Terminazione dei processi...")
        if process1:
            process1.terminate()
            process1.wait()
        if process2:
            process2.terminate()
            process2.wait()
        print("Processi terminati.")