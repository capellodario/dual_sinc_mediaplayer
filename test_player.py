import vlc
import time
import subprocess
import re
import os

def get_screen_resolution():
    """
    Usa `tvservice` e `fbset` per ottenere la risoluzione attiva dell'HDMI.
    """
    try:
        # tvservice mostra le info HDMI
        output = subprocess.check_output(["tvservice", "-s"]).decode()
        # Cerca una stringa tipo "1920x1080"
        match = re.search(r"(\d{3,4})x(\d{3,4})", output)
        if match:
            return int(match.group(1)), int(match.group(2))
        else:
            raise ValueError("Risoluzione non trovata in output tvservice.")
    except Exception as e:
        print(f"[ERRORE] Impossibile determinare risoluzione: {e}")
        return 1280, 720  # fallback sicuro

def play_video_fullscreen(video_path):
    width, height = get_screen_resolution()
    print(f"[INFO] Risoluzione HDMI rilevata: {width}x{height}")

    # Crea istanza VLC con accelerazione hardware DRM (se supportata)
    instance = vlc.Instance([
        "--vout=drm",
        "--avcodec-hw=drm",
        "--fullscreen",
        "--no-osd",
        "--no-video-title-show",
        "--quiet"
    ])

    media = instance.media_new(video_path)
    player = instance.media_player_new()
    player.set_media(media)

    # Tenta di forzare fullscreen (può non funzionare senza X11)
    player.play()
    time.sleep(1)

    state = player.get_state()
    print(f"[INFO] Stato iniziale del player: {state}")

    try:
        while True:
            state = player.get_state()
            if state == vlc.State.Ended:
                print("[INFO] Video terminato. Riparte.")
                player.stop()
                player.play()
            elif state == vlc.State.Error:
                print("[ERRORE] Errore nella riproduzione.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("[INFO] Interrotto dall'utente.")
        player.stop()

if __name__ == "__main__":
    video_file = "test_vid.mp4"  # Assicurati che sia in H.264!
    if os.path.exists(video_file):
        play_video_fullscreen(video_file)
    else:
        print(f"[ERRORE] File video non trovato: {video_file}")
