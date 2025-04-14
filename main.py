import subprocess
import time
import os

video_path = "/media/muchomas/rasp_key/il_tuo_video_7680x2160.mp4"  # Sostituisci con il nuovo percorso

def play_spanned_video(video_path):
    """Riproduce il video a schermo intero."""
    command = [
        "/usr/bin/mpv",
        "--fullscreen=yes",
        "--loop",
        "--no-osc",
        video_path
    ]
    print(f"Avvio video a schermo intero: {command}")
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process

if __name__ == "__main__":
    time.sleep(3)  # Attendi che l'ambiente desktop sia pronto

    video_process = play_spanned_video(video_path)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Terminazione del processo video...")
        if video_process:
            video_process.terminate()
            video_process.wait()
        print("Processo video terminato.")