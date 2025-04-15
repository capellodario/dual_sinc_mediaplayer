import vlc
import time

video_path = "/media/muchomas/rasp_key/test_2.mp4"  # Assicurati che questo sia corretto

instance = vlc.Instance()
player = instance.media_player_new()
media = instance.media_new(video_path)
player.set_media(media)
player.play()

time.sleep(10)  # Riproduci per 10 secondi

player.stop() 