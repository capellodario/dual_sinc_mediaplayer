import subprocess
import time
import os
import glob
import shutil

# --- Configurazione ---
TARGET_FILES = ["1.mp4", "2.mp4", "3.mp4"]
LOCAL_VIDEO_DIR = "/home/pi/videos"  # Cambia con la directory desiderata sul Raspberry Pi
MOUNT_POINT_PREFIX = "/media/MuchoMas!/"

# --- Configurazione Schermi (Modificare in base alla propria configurazione) ---
DISPLAY1_WIDTH = 1024
DISPLAY1_HEIGHT = 600
DISPLAY1_OFFSET_X = 0
DISPLAY1_OFFSET_Y = 0

DISPLAY2_WIDTH = 1152
DISPLAY2_HEIGHT = 864
DISPLAY2_OFFSET_X = 1024
DISPLAY2_OFFSET_Y = 0

# --- Funzioni ---
def find_usb_drive():
    """Cerca le unità USB montate e restituisce il percorso alla prima trovata."""
    print(f"Ricerca unità USB in: {MOUNT_POINT_PREFIX}*")
    mounted_drives = glob.glob(f"{MOUNT_POINT_PREFIX}*")
    print(f"Unità trovate: {mounted_drives}")
    if mounted_drives:
        return mounted_drives[0]
    return None

def copy_files_from_usb(usb_path, local_dir, target_files):
    """Copia i file specificati dall'unità USB alla directory locale, eliminando i precedenti."""
    print(f"Copia dei file da {usb_path} a {local_dir}")
    if os.path.exists(local_dir):
        print(f"Eliminazione dei file precedenti in {local_dir}")
        for item in os.listdir(local_dir):
            item_path = os.path.join(local_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"Errore durante l'eliminazione di {item_path}: {e}")
    else:
        os.makedirs(local_dir, exist_ok=True)
        print(f"Creata la directory: {local_dir}")

    copied_files = []
    for filename in target_files:
        source_path = os.path.join(usb_path, filename)
        dest_path = os.path.join(local_dir, filename)
        if os.path.exists(source_path):
            try:
                shutil.copy2(source_path, dest_path)
                copied_files.append(dest_path)
                print(f"Copiato: {source_path} a {dest_path}")
            except Exception as e:
                print(f"Errore durante la copia di {source_path}: {e}")
        else:
            print(f"File non trovato sull'USB: {source_path}")
    return copied_files

def find_local_media_files(local_dir, target_files):
    """Cerca i file video e audio specifici nella directory locale."""
    print(f"Ricerca file multimediali in: {local_dir}")
    video1_path = os.path.join(local_dir, target_files[0])
    video2_path = os.path.join(local_dir, target_files[1])
    audio_path = os.path.join(local_dir, target_files[2])

    print(f"Percorso video 1 cercato: {video1_path}")
    print(f"Percorso video 2 cercato: {video2_path}")
    print(f"Percorso audio cercato: {audio_path}")

    if os.path.exists(video1_path) and os.path.exists(video2_path) and os.path.exists(audio_path):
        print("File multimediali locali trovati.")
        return video1_path, video2_path, audio_path
    else:
        print("File multimediali locali NON trovati.")
        return None, None, None

def play_video_mpv(video_path, width, height, offset_x, offset_y):
    display_env = {
        **os.environ,
        "DISPLAY": ":0"
    }

    command = [
        "mpv",
        "--fullscreen=yes",
        "--loop-file=inf",
        "--no-border",
        f"--geometry={width}x{height}+{offset_x}+{offset_y}",
        "--hwdec=auto",
        "--profile=low-latency",
        "--no-audio",
        "--fps=30",
        "--cache=yes",
        "--cache-secs=10",
        "--no-osc",
        "--no-osd-bar",
        "--osd-level=0",
        video_path
    ]

    process = subprocess.Popen(command, env=display_env)
    return process

def play_audio_mpv(audio_path):
    command = [
        "mpv",
        "--no-video",
        "--loop-file=inf",
        "--no-terminal",
        audio_path
    ]
    process = subprocess.Popen(command)
    return process

if __name__ == "__main__":
    time.sleep(10)
    print("Avvio gestione file dalla chiavetta USB...")
    usb_path = find_usb_drive()

    if usb_path:
        copy_files_from_usb(usb_path, LOCAL_VIDEO_DIR, TARGET_FILES)
        video1_path, video2_path, audio_path = find_local_media_files(LOCAL_VIDEO_DIR, TARGET_FILES)

        if video1_path and video2_path and audio_path:
            print("Avvio riproduzione video con mpv (fullscreen)...")
            # Riproduzione sul primo schermo
            video_process_1 = play_video_mpv(
                video1_path,
                DISPLAY1_WIDTH,
                DISPLAY1_HEIGHT,
                DISPLAY1_OFFSET_X,
                DISPLAY1_OFFSET_Y
            )
            time.sleep(1)
            # Riproduzione sul secondo schermo
            video_process_2 = play_video_mpv(
                video2_path,
                DISPLAY2_WIDTH,
                DISPLAY2_HEIGHT,
                DISPLAY2_OFFSET_X,
                DISPLAY2_OFFSET_Y
            )

            print("Avvio riproduzione audio...")
            audio_process = play_audio_mpv(audio_path)

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
            print(f"I file richiesti ({', '.join(TARGET_FILES)}) non sono stati trovati nella directory locale: {LOCAL_VIDEO_DIR}")
    else:
        print("Nessuna unità USB trovata. Si tenterà la riproduzione dalla directory locale.")
        video1_path, video2_path, audio_path = find_local_media_files(LOCAL_VIDEO_DIR, TARGET_FILES)
        if video1_path and video2_path and audio_path:
            print("Avvio riproduzione video con mpv (fullscreen)...")
            # Riproduzione sul primo schermo
            video_process_1 = play_video_mpv(
                video1_path,
                DISPLAY1_WIDTH,
                DISPLAY1_HEIGHT,
                DISPLAY1_OFFSET_X,
                DISPLAY1_OFFSET_Y
            )
            time.sleep(1)
            # Riproduzione sul secondo schermo
            video_process_2 = play_video_mpv(
                video2_path,
                DISPLAY2_WIDTH,
                DISPLAY2_HEIGHT,
                DISPLAY2_OFFSET_X,
                DISPLAY2_OFFSET_Y
            )

            print("Avvio riproduzione audio...")
            audio_process = play_audio_mpv(audio_path)

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
            print(f"I file richiesti ({', '.join(TARGET_FILES)}) non sono stati trovati nella directory locale: {LOCAL_VIDEO_DIR}")