import vlc
import time
import subprocess
import os

def usb_video_handler(mount_point="/media/usb_video"):
    """Rileva e monta la prima chiavetta USB disponibile e cerca video"""
    try:
        print("Cercando dispositivi USB...")
        # Trova tutti i dispositivi USB
        lsblk_output = subprocess.run(["lsblk", "-J"],
                                    capture_output=True,
                                    text=True).stdout
        print(f"Dispositivi trovati (lsblk):\n{lsblk_output}")

        # Trova il primo dispositivo rimovibile
        print("Cercando dispositivi con filesystem FAT...")
        devices = subprocess.run(["findfs", "TYPE=vfat"],
                               capture_output=True,
                               text=True).stdout.split('\n')
        print(f"Dispositivi FAT trovati: {devices}")

        if not devices[0]:
            print("Nessun dispositivo FAT trovato")
            return None

        device_path = devices[0]
        print(f"Dispositivo selezionato: {device_path}")

        # Crea punto di mount se non esiste
        if not os.path.exists(mount_point):
            print(f"Creazione punto di mount: {mount_point}")
            subprocess.run(["sudo", "mkdir", "-p", mount_point], check=True)

        # Monta il dispositivo
        if not os.path.ismount(mount_point):
            print(f"Montaggio dispositivo in: {mount_point}")
            subprocess.run(["sudo", "mount", device_path, mount_point], check=True)
        else:
            print("Dispositivo già montato")

        # Cerca video
        print("Ricerca video...")
        video_extensions = ('.mp4', '.avi', '.mkv', '.mov')
        files = os.listdir(mount_point)
        print(f"File trovati nella chiavetta: {files}")

        for item in files:
            if not item.startswith('._') and item.lower().endswith(video_extensions):
                video_path = os.path.join(mount_point, item)
                print(f"Video trovato: {video_path}")
                return video_path

        print("Nessun video trovato")

    except Exception as e:
        print(f"Errore: {str(e)}")
        return None

    return None

def play_video_fullscreen_loop(video_path):
    print(f"Avvio riproduzione: {video_path}")
    instance = vlc.Instance("--vout=egl")
    player = instance.media_player_new(video_path)
    media = instance.media_new(video_path)

    player.set_media(media)
    player.set_fullscreen(True)
    player.play()
    print("Video avviato in fullscreen")

    try:
        while True:
            time.sleep(1)
            if player.get_state() == vlc.State.Ended:
                print("Riavvio video")
                player.set_media(instance.media_new(video_path))
                player.play()
    except KeyboardInterrupt:
        print("\nInterruzione manuale")
        player.stop()
        instance.release()
        print("Riproduzione terminata")

if __name__ == "__main__":
    print("Avvio programma")
    video_path = usb_video_handler()
    if video_path:
        print("Video trovato, avvio riproduzione")
        play_video_fullscreen_loop(video_path)
    else:
        print("Nessun video da riprodurre")
