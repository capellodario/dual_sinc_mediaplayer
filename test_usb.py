import vlc
import time
import subprocess
import os

DEVICE_LABEL = "rasp_key"
MOUNT_POINT = "/media/usb_video"
VIDEO_PATH_RELATIVE = "test_1.mp4"

def mount_usb_by_label(label, mount_point):
    # ... (funzione di montaggio invariata) ...

def play_video_loop_manual(video_path):
    """Riproduce un video in loop manualmente."""
    if os.path.exists(video_path):
        instance = vlc.Instance("--vout=dispmanx", "--avcodec-hw=any")
        if instance is None:
            print("Errore nell'inizializzazione di VLC.")
            return False
        player = instance.media_player_new()
        media = instance.media_new(video_path)
        player.set_media(media)

        print(f"Riproduzione in loop avviata da: {video_path} (premi Ctrl+C per interrompere)")
        try:
            while True:
                player.play()
                while player.is_playing():
                    time.sleep(1)
                player.stop()
                time.sleep(0.5) # Breve pausa prima di riavviare
        except KeyboardInterrupt:
            print("\nRiproduzione interrotta.")
            player.stop()
            instance.release()
            return True
    else:
        print(f"File video non trovato in: {video_path}")
        return False

if __name__ == "__main__":
    if mount_usb_by_label(DEVICE_LABEL, MOUNT_POINT):
        video_full_path = os.path.join(MOUNT_POINT, VIDEO_PATH_RELATIVE)
        play_video_loop_manual(video_full_path)
    else:
        print("Impossibile montare la chiavetta, riproduzione non avviata.")