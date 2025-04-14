import subprocess
import time
import os

video_path = "/media/muchomas/rasp_key/1.mp4"  # Sostituisci con il percorso del tuo video lungo

def play_spanned_video(video_path):
    """Riproduce il video senza forzare fullscreen o adattamento iniziale."""
    command = [
        "/usr/bin/mpv",
        "--loop",
        "--no-osc",
        video_path
    ]
    print(f"Avvio video semplice: {command}")
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process

if __name__ == "__main__":
    time.sleep(30)  # Attendi che l'ambiente desktop sia pronto

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