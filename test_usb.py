import vlc
import time
import subprocess
import os
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEVICE_LABEL = "rasp_key"
MOUNT_POINT = "/media/usb_video"

def mount_usb_by_label(label, mount_point):
    logger.info(f"Tentativo di montaggio USB con label '{label}' su '{mount_point}'")
    try:
        logger.debug("Esecuzione comando blkid per trovare il device...")
        process = subprocess.run(["blkid", "-L", label], capture_output=True, text=True, check=True)
        device_path = process.stdout.strip()
        logger.info(f"Device trovato: {device_path}")

        if not os.path.exists(mount_point):
            logger.debug(f"Creazione punto di montaggio: {mount_point}")
            subprocess.run(["sudo", "mkdir", "-p", mount_point], check=True)
            logger.info("Punto di montaggio creato con successo")

        if device_path and not os.path.ismount(mount_point):
            logger.debug(f"Montaggio device {device_path} su {mount_point}")
            subprocess.run(["sudo", "mount", device_path, mount_point], check=True)
            logger.info("Montaggio completato con successo")
            return True

        is_mounted = os.path.ismount(mount_point)
        logger.info(f"Stato montaggio: {'già montato' if is_mounted else 'non montato'}")
        return is_mounted
    except Exception as e:
        logger.error(f"Errore durante il montaggio: {str(e)}")
        return False

def find_first_valid_video(mount_point):
    logger.info(f"Ricerca video in: {mount_point}")
    video_extensions = ('.mp4', '.avi', '.mkv', '.mov')
    try:
        files = os.listdir(mount_point)
        logger.debug(f"File trovati: {files}")

        for item in files:
            logger.debug(f"Controllo file: {item}")
            if not item.startswith('._') and item.lower().endswith(video_extensions):
                video_path = os.path.join(mount_point, item)
                logger.info(f"Video valido trovato: {video_path}")
                return video_path
        logger.warning("Nessun video valido trovato")
        return None
    except Exception as e:
        logger.error(f"Errore durante la ricerca del video: {str(e)}")
        return None

def play_video_fullscreen_loop(video_path):
    logger.info(f"Avvio riproduzione video: {video_path}")
    try:
        instance = vlc.Instance("--vout=egl")
        player = instance.media_player_new(video_path)
        media = instance.media_new(video_path)
        logger.debug("VLC instance e player creati")

        player.set_media(media)
        player.set_fullscreen(True)
        player.play()
        logger.info("Riproduzione video avviata")

        loop_count = 0
        while True:
            time.sleep(1)
            state = player.get_state()
            logger.debug(f"Stato player: {state}")

            if state == vlc.State.Ended:
                loop_count += 1
                logger.info(f"Video terminato, riavvio ({loop_count}° loop)")
                player.set_media(instance.media_new(video_path))
                player.play()

    except KeyboardInterrupt:
        logger.info("Interruzione manuale ricevuta")
        player.stop()
        instance.release()
        logger.info("Player fermato e risorse rilasciate")
    except Exception as e:
        logger.error(f"Errore durante la riproduzione: {str(e)}")

if __name__ == "__main__":
    logger.info("Avvio programma")

    if mount_usb_by_label(DEVICE_LABEL, MOUNT_POINT):
        logger.info("USB montata con successo")
        video_path = find_first_valid_video(MOUNT_POINT)

        if video_path:
            logger.info("Avvio riproduzione video")
            play_video_fullscreen_loop(video_path)
        else:
            logger.error("Nessun video trovato da riprodurre")
    else:
        logger.error("Impossibile montare l'USB")
