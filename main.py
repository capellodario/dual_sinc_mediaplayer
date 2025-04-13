import subprocess
import time
import os

video_path = "/media/muchomas/rasp_key/1.mp4"  # Sostituisci con il percorso del tuo video lungo

def set_display_spanning():
    """Configura lo spanning dei display XWAYLAND0 e XWAYLAND1."""
    command = [
        "xrandr",
        "--output", "XWAYLAND0", "--mode", "1024x600", "--pos", "0x0",
        "--output", "XWAYLAND1", "--mode", "1920x1080", "--pos", "1024x0", "--right-of", "XWAYLAND0"
    ]
    print("Tentativo di configurare lo spanning dei display...")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if stderr:
        print(f"Errore durante la configurazione dello spanning:\n{stderr.decode()}")
        return False
    else:
        print("Spanning dei display configurato.")
        return True

def play_fullscreen_video(video_path):
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
    time.sleep(5)  # Attendi che l'ambiente desktop sia pronto

    if set_display_spanning():
        time.sleep(2)  # Dai un po' di tempo per l'applicazione dello spanning
        video_process = play_fullscreen_video(video_path)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Terminazione del processo video...")
            if video_process:
                video_process.terminate()
                video_process.wait()
            print("Processo video terminato.")
    else:
        print("Impossibile configurare lo spanning, il video non verrà riprodotto a schermo intero su entrambi i monitor.")