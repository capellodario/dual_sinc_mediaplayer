import subprocess
import time
import os

video1_path = "/media/muchomas/rasp_key/1.mp4"
video2_path = "/media/muchomas/rasp_key/2.mp4"

def play_video_on_display(video_path, display_name):
    command = [
        "/usr/bin/mpv",
        "--fullscreen=yes",
        f"--display-device={display_name}",
        "--loop",
        "--no-osc",
        video_path
    ]
    print(f"Avvio '{video_path}' su display: {display_name}")
    process = subprocess.Popen(command)  # Rimossa la reindirizzazione dell'output
    return process

if __name__ == "__main__":
    time.sleep(5)

    process1 = play_video_on_display(video1_path, "XWAYLAND0")
    time.sleep(0.5)  # Piccolo ritardo per tentare la sincronizzazione
    process2 = play_video_on_display(video2_path, "XWAYLAND1")

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