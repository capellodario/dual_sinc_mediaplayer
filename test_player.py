import vlc
import time

# Sostituisci con il percorso del tuo video
VIDEO_PATH = "test_vid.mp4"

def main():
    # Crea l'istanza di VLC
    instance = vlc.Instance([
        "--avcodec-hw=drm",  # Utilizza accelerazione hardware se supportata
        "--vout=drm",        # Usa l'output video DRM (senza X11)
        "--fullscreen",      # Imposta il video a schermo intero
        "--no-osd",          # Disabilita i messaggi OSD
        "--no-video-title-show",  # Disabilita il titolo del video
        "--quiet"            # Meno output nei log
    ])

    # Crea un player
    player = instance.media_player_new()

    # Crea un media dal percorso
    media = instance.media_new(VIDEO_PATH)
    player.set_media(media)

    # Riproduci il video
    player.play()
    time.sleep(1)

    # Loop per monitorare lo stato del player
    print("[INFO] Avvio del video...")
    try:
        while True:
            state = player.get_state()
            if state == vlc.State.Ended:
                print("[INFO] Video finito. Riparte.")
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
