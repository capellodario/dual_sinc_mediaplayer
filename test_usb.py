import vlc
import time
import subprocess
import os
import logging

logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MOUNT_POINT = "/media/usb_video"
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov')

def find_usb_with_videos():
    """Trova la prima chiavetta USB che contiene video"""
    try:
        # Lista tutti i dispositivi USB
        cmd = "lsblk -o NAME,FSTYPE,TYPE,MOUNTPOINT | grep 'usb' | grep 'part'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        devices = result.stdout.strip().split('\n')

        for device in devices:
            logger.info(f"Dispositivo trovato: {device}")
            dev_name = f"/dev/{device.split()[0]}"

            # Monta il dispositivo se non è già montato
            if not os.path.ismount(MOUNT_POINT):
                os.makedirs(MOUNT_POINT, exist_ok=True)
                try:
                    subprocess.run(["sudo", "mount", dev_name, MOUNT_POINT], check=True)
                    logger.info(f"Dispositivo {dev_name} montato su {MOUNT_POINT}")
                except:
                    logger.warning(f"Impossibile montare {dev_name}")
                    continue

            # Cerca video valido usando la stessa logica di prima
            video_path = find_first_valid_video(MOUNT_POINT)
            if video_path:
                return video_path

            # Se non trova video, smonta e prova il prossimo
            subprocess.run(["sudo", "umount", MOUNT_POINT], check=True)

        logger.warning("Nessun video trovato su dispositivi USB")
        return None

    except Exception as e:
        logger.error(f"Errore nella ricerca USB: {str(e)}")
        return None

def find_first_valid_video(mount_point):
    logger.info(f"Ricerca video in: {mount_point}")
    try:
        files = os.listdir(mount_point)
        logger.debug(f"File trovati: {files}")

        for item in files:
            logger.debug(f"Controllo file: {item}")
            if not item.startswith('._') and item.lower().endswith(VIDEO_EXTENSIONS):
                video_path = os.path.join(mount_point, item)
                logger.info(f"Video valido trovato: {video_path}")
                return video_path
        logger.warning("Nessun video valido trovato")
        return None
    except Exception as e:
        logger.error(f"Errore durante la ricerca del video: {str(e)}")
        return None

def play_video_fullscreen_loop(video_path):
    logger.info(f"Avvio riproduzione: {video_path}")
    try:
        instance = vlc.Instance("--vout=egl")
        player = instance.media_player_new(video_path)
        media = instance.media_new(video_path)
        player.set_media(media)
        player.set_fullscreen(True)
        player.play()

        while True:
            time.sleep(1)
            if player.get_state() == vlc.State.Ended:
                player.set_media(instance.media_new(video_path))
                player.play()

    except KeyboardInterrupt:
        player.stop()
        instance.release()
        logger.info("Riproduzione interrotta")
    except Exception as e:
        logger.error(f"Errore riproduzione: {str(e)}")

if __name__ == "__main__":
    logger.info("Ricerca dispositivo USB con video...")
    video_path = find_usb_with_videos()

    if video_path:
        play_video_fullscreen_loop(video_path)
    else:
        logger.error("Nessun video trovato da riprodurre")
