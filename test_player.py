import vlc
import time
import os

VIDEO_PATH = "test_vid.mp4"

def main():
    if not os.path.exists(VIDEO_PATH):
        print(f"[ERRORE] File non trovato: {VIDEO_PATH}")
        return

    print("[INFO] Avvio player VLC in loop, con accelerazione DRM.")

    # Crea istanza VLC con output DRM (no GUI)
    instance = vlc.Instance([
        "--avcodec-hw=drm",
        "--vout=drm",
        "--fullscreen",
        "--no-osd",
        "--no-video-title-show",
        "--quiet"
    ])

    player = instance.media_player_new()
    media = instance.media_new(VIDEO_PATH)
    player.set_media(media)

    player.play()
    time.sleep(1)

    print("[INFO] Video in esecuzione. Ctrl+C per uscire.")

    try:
        while True:
            state = player.get_state()
            if state == vlc.State.Ended:
                print("[INFO] Video terminato. Riparte.")
                player.stop()
                player.play()
            elif state == vlc.State.Error:
                print("[ERRORE] VLC ha riscontrato un errore.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Interruzione manuale.")
        player.stop()

if __name__ == "__main__":
    main()
