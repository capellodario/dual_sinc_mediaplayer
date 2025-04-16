import vlc
import time


def play_loop(video_path):
    instance = vlc.Instance([
        "--vout=drm",              # Usa Direct Rendering Manager
        "--avcodec-hw=drm",        # Accelerazione hardware
        "--fullscreen",            # Schermo intero
        "--no-osd",                # Niente overlay testuale
        "--no-video-title-show",  # Nessun titolo video
        "--quiet"                  # Silenzia log
    ])

    player = instance.media_player_new()
    media = instance.media_new(video_path)
    player.set_media(media)

    player.play()
    time.sleep(0.1)

    while True:
        state = player.get_state()
        if state == vlc.State.Ended:
            player.stop()
            player.play()
        time.sleep(0.5)

if __name__ == "__main__":
    play_loop("test_vid.mp4")
