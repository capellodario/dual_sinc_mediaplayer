import vlc
import time
import subprocess
import os

DEVICE_LABEL = "rasp_key"
MOUNT_POINT = "/media/usb_video"

def mount_usb_by_label(label, mount_point):
    try:
        device_path = subprocess.run(["blkid", "-L", label], capture_output=True, text=True, check=True).stdout.strip()

        if not os.path.exists(mount_point):
            subprocess.run(["sudo", "mkdir", "-p", mount_point], check=True)

        if device_path and not os.path.ismount(mount_point):
            subprocess.run(["sudo", "mount", device_path, mount_point], check=True)
            return True
        return os.path.ismount(mount_point)
    except:
        return False

def find_first_valid_video(mount_point):
    video_extensions = ('.mp4', '.avi', '.mkv', '.mov')
    try:
        for item in os.listdir(mount_point):
            if not item.startswith('._') and item.lower().endswith(video_extensions):
                return os.path.join(mount_point, item)
        return None
    except:
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
    if mount_usb_by_label(DEVICE_LABEL, MOUNT_POINT):
        video_path = find_first_valid_video(MOUNT_POINT)
        if video_path:
            play_video_fullscreen_loop(video_path)
