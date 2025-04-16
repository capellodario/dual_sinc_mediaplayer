import vlc
import time
video_file = "test_vid.mp4"

def play_4k_loop(video_path):
    """
    Riproduce un video 4K a 30fps in loop sullo schermo interno di un Raspberry Pi 4B
    con Debian Light (senza desktop) utilizzando python-vlc.

    Args:
        video_path (str): Il percorso completo del file video 4K.
    """
    try:
        # Crea un'istanza di VLC
        instance = vlc.Instance()

        # Crea un oggetto Media
        media = instance.media_new(video_path)

        # Crea un Media Player
        player = instance.media_player_new()

        # Imposta il Media nel Player
        player.set_media(media)

        # Imposta l'uscita video per la console (framebuffer)
        # Questo è fondamentale per l'esecuzione senza ambiente desktop
        player.set_xwindow(0)  # 0 indica l'uscita predefinita (framebuffer)

        # Avvia la riproduzione
        player.play()

        # Imposta la riproduzione in loop
        player.set_loop(True)

        print(f"Riproduzione in loop di: {video_path} (4K 30fps)")
        print("Premi Ctrl+C per interrompere.")

        # Mantieni lo script in esecuzione per consentire la riproduzione
        while True:
            time.sleep(1)

    except vlc.VLCError as e:
        print(f"Errore VLC: {e}")
    except KeyboardInterrupt:
        print("\nRiproduzione interrotta dall'utente.")
    finally:
        # Pulisci le risorse
        if 'player' in locals() and player.is_playing():
            player.stop()
        if 'player' in locals():
            player.release()
        if 'instance' in locals():
            instance.release()

if __name__ == "__main__":


    # Verifica che il file video esista
    import os
    if not os.path.exists(video_file):
        print(f"Errore: Il file video '{video_file}' non è stato trovato.")
    else:
        play_4k_loop(video_file)
