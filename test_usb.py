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

def find_first_valid_video(mount_point):
    """Trova il percorso del primo file video valido nel punto di mount."""
    video_extensions = ('.mp4', '.avi', '.mkv', '.mov')
    try:
        items = os.listdir(mount_point)
        for item in items:
            if not item.startswith('._') and item.lower().endswith(video_extensions):
                return os.path.join(mount_point, item)
        print(f"Nessun file video valido trovato in: {mount_point}")
        return None
    except FileNotFoundError:
        print(f"Punto di mount non trovato: {mount_point}")
        return None
    except Exception as e:
        print(f"Si è verificato un errore nella ricerca dei video: {e}")
        return None


def play_video_fullscreen_loop_with_assertions(video_path):
    """Riproduce un video a schermo intero in loop con asserzioni per la verifica."""
    assert isinstance(video_path, str), "video_path deve essere una stringa"
    assert os.path.exists(video_path), f"Il file video non esiste nel percorso: {video_path}"

    instance = vlc.Instance()
    assert instance is not None, "Impossibile creare l'istanza VLC"

    player = instance.media_player_new(video_path)
    assert player is not None, "Impossibile creare il media player VLC"

    media = instance.media_new(video_path)
    assert media is not None and media.get_mrl() == f"file://{os.path.abspath(video_path)}", f"Impossibile creare il media VLC per: {video_path}"

    player.set_media(media)
    player.set_fullscreen(True)
    assert player.get_fullscreen(), "Impossibile impostare la modalità a schermo intero"

    player.play()
    assert player.is_playing(), "Impossibile avviare la riproduzione del video"
    print(f"Riproduzione in loop avviata: {video_path}")

    try:
        while True:
            time.sleep(1)
            assert player.get_state() in [vlc.State.Playing, vlc.State.Ended], f"Stato del player inatteso: {player.get_state()}"
            if player.get_state() == vlc.State.Ended:
                player.set_media(instance.media_new(video_path))
                player.play()
                assert player.is_playing(), "Impossibile riavviare la riproduzione del video"
                print("Riavvio.")
    except KeyboardInterrupt:
        print("Interruzione manuale.")
    finally:
        player.stop()
        assert player.get_state() == vlc.State.Ended or player.get_state() == vlc.State.Stopped, f"Stato del player inatteso dopo lo stop: {player.get_state()}"
        instance.release()
        print("Risorse VLC rilasciate.")


if __name__ == "__main__":
    
    if mount_usb_by_label(DEVICE_LABEL, MOUNT_POINT):
        video_to_play = find_first_valid_video(MOUNT_POINT)
        if video_to_play:
            play_video_fullscreen_loop_with_assertions(video_to_play)
        else:
            print("Nessun video da riprodurre.")
    else:
        print("Impossibile montare la chiavetta, riproduzione non avviata.")