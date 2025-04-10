import subprocess
import time
import os
import glob
import shutil  # For copying files (optional, see explanation)

# --- Configurazione ---
TARGET_FILES = ["1.mp4", "2.mp4", "3.mp4"]
MOUNT_POINT_PREFIX = "/media/pi/"  # Default mount point for USB drives in Raspberry Pi OS

DISPLAY_HDMI_1_X = 0
DISPLAY_HDMI_1_Y = 0
DISPLAY_HDMI_2_X = 1920  # Adjust based on your screen width
DISPLAY_HDMI_2_Y = 0

# --- Funzioni ---
def find_usb_drive():
    """Cerca le unità USB montate e restituisce il percorso alla prima trovata."""
    mounted_drives = glob.glob(f"{MOUNT_POINT_PREFIX}*")
    if mounted_drives:
        return mounted_drives[0]
    return None

def find_media_files(usb_path):
    """Cerca i file video e audio specifici nell'unità USB."""
    video1_path = os.path.join(usb_path, TARGET_FILES[0])
    video2_path = os.path.join(usb_path, TARGET_FILES[1])
    audio_path = os.path.join(usb_path, TARGET_FILES[2])

    if os.path.exists(video1_path) and os.path.exists(video2_path) and os.path.exists(audio_path):
        return video1_path, video2_path, audio_path
    return None, None, None

def play_video_ffplay(video_path, x, y, width, height):
    command = [
        "ffplay",
        "-fs",
        "-noborder",
        "-window_x", str(x),
        "-window_y", str(y),
        "-window_width", str(width),
        "-window_height", str(height),
        "-loop", "0",
        video_path
    ]
    process = subprocess.Popen(command)
    return process

def play_audio_ffplay(audio_path):
    command = [
        "ffplay",
        "-nodisp",
        "-autoexit",
        audio_path
    ]
    process = subprocess.Popen(command)
    return process

def get_display_resolution(display_id):
    try:
        output = subprocess.check_output(["xrandr", "--listmonitors"]).decode("utf-8")
        for line in output.splitlines():
            if f"Monitor {display_id}:" in line:
                resolution_match = re.search(r"(\d+)x(\d+)\+", line)
                if resolution_match:
                    return int(resolution_match.group(1)), int(resolution_match.group(2))
        return None
    except FileNotFoundError:
        print("Errore: xrandr non trovato. Assicurati che sia installato.")
        return None
    except Exception as e:
        print(f"Si è verificato un errore durante l'ottenimento della risoluzione: {e}")
        return None

if __name__ == "__main__":
    import re

    print("Ricerca unità USB...")
    usb_path = find_usb_drive()

    if usb_path:
        print(f"Unità USB trovata in: {usb_path}")
        video1_path, video2_path, audio_path = find_media_files(usb_path)

        if video1_path and video2_path and audio_path:
            print("File multimediali trovati.")

            # Ottieni le risoluzioni degli schermi
            resolution1 = get_display_resolution(0)
            resolution2 = get_display_resolution(1)

            if not resolution1 or not resolution2:
                print("Errore: Impossibile ottenere la risoluzione di uno o entrambi i monitor.")
                exit(1)

            width1, height1 = resolution1
            width2, height2 = resolution2

            print("Avvio riproduzione video con ffplay...")
            video_process_1 = play_video_ffplay(video1_path, DISPLAY_HDMI_1_X, DISPLAY_HDMI_1_Y, width1, height1)
            time.sleep(0.1)
            video_process_2 = play_video_ffplay(video2_path, DISPLAY_HDMI_2_X, DISPLAY_HDMI_2_Y, width2, height2)

            print("Avvio riproduzione audio con ffplay...")
            audio_process = play_audio_ffplay(audio_path)

            try:
                video_process_1.wait()
                video_process_2.wait()
                audio_process.wait()
            except KeyboardInterrupt:
                print("\nInterruzione manuale. Terminazione dei processi...")
                video_process_1.terminate()
                video_process_2.terminate()
                audio_process.terminate()
                video_process_1.wait()
                video_process_2.wait()
                audio_process.wait()
                print("Processi terminati.")

        else:
            print(f"I file richiesti ({', '.join(TARGET_FILES)}) non sono stati trovati nell'unità USB.")
    else:
        print("Nessuna unità USB trovata.")