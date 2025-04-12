import subprocess
import time
import os
import glob
import shutil

# --- Configurazione ---
TARGET_FILES = ["1.mp4"]  # Solo il video unito
MOUNT_POINT_PREFIX = "/media/MuchoMas!/"
LOCAL_VIDEO_DIR = "/home/MuchoMas!/videos"

# --- Configurazione Schermi (Larghezza totale dello schermo esteso) ---
DISPLAY1_WIDTH = 1152 # Assumendo 4K orizzontale
DISPLAY1_HEIGHT = 1024
DISPLAY2_WIDTH = 864 # Assumendo 4K orizzontale
DISPLAY2_HEIGHT = 600

TOTAL_WIDTH = DISPLAY1_WIDTH + DISPLAY2_WIDTH  # Larghezza totale dello schermo esteso (7680)
TOTAL_HEIGHT = max(DISPLAY1_HEIGHT, DISPLAY2_HEIGHT) # Altezza 2160

DISPLAY_OFFSET_X = 0
DISPLAY_OFFSET_Y = 0

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
    """Cerca i file video specifici nella directory locale."""
    print(f"Ricerca file multimediali in: {local_dir}")
    video_path = os.path.join(local_dir, target_files[0])

    print(f"Percorso video cercato: {video_path}")

    if os.path.exists(video_path):
        print("File video locale trovato.")
        return video_path, None  # Restituiamo None per il file audio
    else:
        print("File video locale NON trovato.")
        return None, None

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

if __name__ == "__main__":
    time.sleep(10)
    print("Avvio gestione file dalla chiavetta USB...")
    usb_path = find_usb_drive()

    if usb_path:
        copy_files_from_usb(usb_path, LOCAL_VIDEO_DIR, TARGET_FILES)
        video_path, _ = find_local_media_files(LOCAL_VIDEO_DIR, TARGET_FILES)

        if video_path:
            print("Avvio riproduzione video unito (fullscreen)...")
            video_process = play_video_mpv(
                video_path,
                TOTAL_WIDTH,
                TOTAL_HEIGHT,
                DISPLAY_OFFSET_X,
                DISPLAY_OFFSET_Y
            )

            try:
                video_process.wait()
            except KeyboardInterrupt:
                print("\nInterruzione manuale. Terminazione del processo video...")
                video_process.terminate()
                video_process.wait()
                print("Processo video terminato.")

        else:
            print(f"File video unito ({TARGET_FILES[0]}) non trovato nella directory locale: {LOCAL_VIDEO_DIR}")
    else:
        print("Nessuna unità USB trovata. Si tenterà la riproduzione dalla directory locale.")
        video_path, _ = find_local_media_files(LOCAL_VIDEO_DIR, TARGET_FILES)
        if video_path:
            print("Avvio riproduzione video unito (fullscreen)...")
            video_process = play_video_mpv(
                video_path,
                TOTAL_WIDTH,
                TOTAL_HEIGHT,
                DISPLAY_OFFSET_X,
                DISPLAY_OFFSET_Y
            )

            try:
                video_process.wait()
            except KeyboardInterrupt:
                print("\nInterruzione manuale. Terminazione del processo video...")
                video_process.terminate()
                video_process.wait()
                print("Processo video terminato.")
        else:
            print(f"File video unito ({TARGET_FILES[0]}) non trovato nella directory locale: {LOCAL_VIDEO_DIR}")