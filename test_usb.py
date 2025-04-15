import vlc
import time
import subprocess
import os

DEVICE_LABEL = "rasp_key"  # Etichetta del file system della tua chiavetta
MOUNT_POINT = "/media/usb_video" # Punto di mount desiderato
VIDEO_PATH_RELATIVE = "test_1.mp4" # Percorso relativo del video sulla chiavetta

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

def play_video_from_path_loop(video_path):
    """Riproduce un video in loop dal percorso specificato."""
    if os.path.exists(video_path):
        # Forza l'output su dispmanx e abilita l'accelerazione hardware
        instance = vlc.Instance("--vout=dispmanx", "--hwtimer-system", "--avcodec-hw=any")
        player = instance.media_player_new()
        media = instance.media_new(video_path)
        player.set_media(media)
        player.set_loop(True)  # Imposta la riproduzione in loop
        player.play()
        print(f"Riproduzione in loop avviata da: {video_path} (premi Ctrl+C per interrompere)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nRiproduzione interrotta.")
            player.stop()
            instance.release() # Rilascia l'istanza VLC
            return True
    else:
        print(f"File video non trovato in: {video_path}")
        return False

if __name__ == "__main__":
    if mount_usb_by_label(DEVICE_LABEL, MOUNT_POINT):
        video_full_path = os.path.join(MOUNT_POINT, VIDEO_PATH_RELATIVE)
        play_video_from_path_loop(video_full_path)
    else:
        print("Impossibile montare la chiavetta, riproduzione non avviata.")