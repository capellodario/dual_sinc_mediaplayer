import vlc
import time
import subprocess
import os

def usb_video_handler(mount_point="/media/usb_video"):
    """Rileva e monta la prima chiavetta USB disponibile e cerca video"""
    try:
        # Trova tutti i dispositivi USB
        lsblk_output = subprocess.run(["lsblk", "-J"],
                                    capture_output=True,
                                    text=True).stdout

        # Trova il primo dispositivo rimovibile (tipicamente chiavetta USB)
        devices = subprocess.run(["findfs", "TYPE=vfat"],
                               capture_output=True,
                               text=True).stdout.split('\n')

        if not devices[0]:
            return None

        device_path = devices[0]

        # Crea punto di mount se non esiste
        if not os.path.exists(mount_point):
            subprocess.run(["sudo", "mkdir", "-p", mount_point], check=True)

        # Monta il dispositivo
        if not os.path.ismount(mount_point):
            subprocess.run(["sudo", "mount", device_path, mount_point], check=True)

        # Cerca video
        video_extensions = ('.mp4', '.avi', '.mkv', '.mov')
        for item in os.listdir(mount_point):
            if not item.startswith('._') and item.lower().endswith(video_extensions):
                return os.path.join(mount_point, item)

    except Exception as e:
        return None

    return None

def play_video_fullscreen_loop(video_path):
    instance = vlc.Instance("--vout=egl")
    player = instance.media_player_new(video_path)
    media = instance.media_new(video_path)

    player.set_media(media)
    player.set_fullscreen(True)
    player.play()

    try:
        while True:
            time.sleep(1)
            if player.get_state() == vlc.State.Ended:
                player.set_media(instance.media_new(video_path))
                player.play()
    except KeyboardInterrupt:
        player.stop()
        instance.release()

if __name__ == "__main__":
    video_path = usb_video_handler()
    if video_path:
        play_video_fullscreen_loop(video_path)
