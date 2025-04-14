import subprocess
import time
import os
import glob

def find_first_video(mount_point="/media/muchomas"):
    """
    Cerca la prima chiavetta USB montata e restituisce il percorso
    del primo file video trovato al suo interno.
    """
    chiavette = glob.glob(f"{mount_point}/rasp_key*")  # Cerca directory che iniziano con rasp_key
    if chiavette:
        first_chiavetta = chiavette[0]
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov']  # Estensioni video comuni
        for root, _, files in os.walk(first_chiavetta):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    return os.path.join(root, file)
        print(f"Nessun file video trovato nella chiavetta: {first_chiavetta}")
        return None
    else:
        print("Nessuna chiavetta USB 'rasp_key*' trovata.")
        return None

def play_fullscreen_video(video_path):
    """
    Riproduce il video a schermo intero utilizzando mpv.
    """
    command = [
        "mpv",
        "--fullscreen",
        video_path
    ]
    print(f"Avvio video a schermo intero con mpv: {command}")
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process

if __name__ == "__main__":
    time.sleep(3)  # Attendi che le unità siano montate

    video_file = find_first_video()

    if video_file:
        print(f"Trovato il video: {video_file}")
        video_process = play_fullscreen_video(video_file)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            if video_process:
                video_process.terminate()
                video_process.wait()
            print("Processo video terminato.")
    else:
        print("Nessun video da riprodurre.")