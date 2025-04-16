import vlc
import time

VIDEO_PATH = "test_h265.mp4"

def main():
    instance = vlc.Instance(["--no-video-title-show", "--quiet"])
    player = instance.media_player_new()
    media = instance.media_new(VIDEO_PATH)
    player.set_media(media)

    player.play()
    time.sleep(2)  # Aspetta che il video inizi

    while player.is_playing():
        time.sleep(1)  # Mantieni il video in esecuzione

    print("Video terminato.")

if __name__ == "__main__":
    main()
