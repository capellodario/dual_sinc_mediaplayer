import vlc
import time
import os

video_file = "test_vid.mp4"

def play_4k_loop(video_path):
    """
    Riproduce un video in loop sullo schermo interno utilizzando la playlist.

    Args:
        video_path (str): Il percorso completo del file video.
    """
    try:
        # Crea un'istanza di VLC
        instance = vlc.Instance()

        # Crea un MediaList
        media_list = instance.media_list_new([video_path])

        # Crea un MediaListPlayer
        list_player = instance.media_list_player_new()

        # Imposta la MediaList nel MediaListPlayer
        list_player.set_media_list(media_list)

        # Imposta l'uscita video per la console (framebuffer)
        # Fondamentale per l'esecuzione senza ambiente desktop
        player = list_player.get_media_player()
        player.set_xwindow(0)  # 0 indica l'uscita predefinita (framebuffer)

        # Imposta la riproduzione in loop della playlist
        list_player.set_playback_mode(vlc.PlaybackMode.loop)

        # Avvia la riproduzione
        list_player.play()

        print(f"Riproduzione in loop di: {video_path}")
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
        if 'list_player' in locals() and list_player.is_playing():
            list_player.stop()
        if 'list_player' in locals():
            list_player.release()
        if 'instance' in locals():
            instance.release()

if __name__ == "__main__":
    if not os.path.exists(video_file):
        print(f"Errore: Il file video '{video_file}' non è stato trovato.")
    else:
        play_4k_loop(video_file)
