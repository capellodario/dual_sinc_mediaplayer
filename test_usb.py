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

def play_video_fullscreen_loop(video_path):
    """Riproduce un video a schermo intero in loop."""
    if not os.path.exists(video_path):
        print(f"Errore: File non trovato: {video_path}")
        return

    instance = vlc.Instance()
    player = instance.media_player_new(video_path)
    player.set_fullscreen(True)
    player.play()
    print(f"Riproduzione in loop avviata: {video_path}")

    while True:
        time.sleep(1)
        if player.get_state() == vlc.State.Ended:
            player.set_media(instance.media_new(video_path))
            player.play()
            print("Riavvio.")


if __name__ == "__main__":
    if mount_usb_by_label(DEVICE_LABEL, MOUNT_POINT):
        play_first_valid_video_once(MOUNT_POINT)
    else:
        print("Impossibile montare la chiavetta, riproduzione non avviata.")