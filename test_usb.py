import vlc
import time
import subprocess
import os

DEVICE_LABEL = "rasp_key"  # Etichetta del file system della tua chiavetta
MOUNT_POINT = "/media/usb_video" # Punto di mount desiderato

def mount_usb_by_label(label, mount_point):
    """Monta un dispositivo USB in base alla sua etichetta."""
    device_path = None
    try:
        result = subprocess.run(["blkid", "-L", label], capture_output=True, text=True, check=True)
        device_path = result.stdout.strip()
        print(f"Trovato dispositivo con etichetta '{label}' in: {device_path}")
    except subprocess.CalledProcessError:
        print(f"Dispositivo con etichetta '{label}' non trovato.")
        return False

    if not os.path.exists(mount_point):
        try:
            subprocess.run(["sudo", "mkdir", "-p", mount_point], check=True)
            print(f"Creato punto di mount: {mount_point}")
        except subprocess.CalledProcessError as e:
            print(f"Errore nella creazione del punto di mount: {e}")
            return False

    if device_path and not os.path.ismount(mount_point):
        try:
            subprocess.run(["sudo", "mount", device_path, mount_point], check=True)
            print(f"Dispositivo montato su: {mount_point}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Errore nel montaggio: {e}")
            return False
    elif os.path.ismount(mount_point):
        print(f"Il dispositivo con etichetta '{label}' è già montato su: {mount_point}")
        return True
    else:
        return False

def play_first_valid_video_once(mount_point):
    """Riproduce una volta il primo file video valido trovato nel punto di mount."""
    try:
        video_extensions = ('.mp4', '.avi', '.mkv', '.mov')
        video_files = [
            f for f in os.listdir(mount_point)
            if f.endswith(video_extensions) and not f.startswith('._')
        ]
        if video_files:
            video_path = os.path.join(mount_point, video_files[0])
            print(f"Trovato file video valido: {video_path}")
            instance = vlc.Instance("--vout=dispmanx", "--avcodec-hw=any")
            if instance is None:
                print("Errore nell'inizializzazione di VLC.")
                return False
            player = instance.media_player_new()
            media = instance.media_new(video_path)
            player.set_media(media)
            player.play()
            print(f"Riproduzione avviata da: {video_path}")
            while player.is_playing():
                time.sleep(1)
            print("Riproduzione completata.")
            player.stop()
            instance.release()
            return True
        else:
            print(f"Nessun file video valido trovato in: {mount_point}")
            return False
    except FileNotFoundError:
        print(f"Punto di mount non trovato: {mount_point}")
        return False
    except Exception as e:
        print(f"Si è verificato un errore durante la ricerca dei file video: {e}")
        return False

if __name__ == "__main__":
    if mount_usb_by_label(DEVICE_LABEL, MOUNT_POINT):
        play_first_valid_video_once(MOUNT_POINT)
    else:
        print("Impossibile montare la chiavetta, riproduzione non avviata.")