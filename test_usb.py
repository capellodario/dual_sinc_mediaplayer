import vlc
import time
import subprocess
import os
import json

def usb_video_handler(mount_point="/media/usb_video"):
    try:
        print("Cercando dispositivi USB...")
        # Trova tutti i dispositivi USB
        lsblk_output = subprocess.run(["lsblk", "-J", "-o", "NAME,RM,TYPE,MOUNTPOINTS"],
                                    capture_output=True,
                                    text=True).stdout
        devices = json.loads(lsblk_output)

        # Cerca specificamente dispositivi rimovibili (RM=1)
        usb_device = None
        for device in devices['blockdevices']:
            print(f"Analisi dispositivo: {device['name']} (rimovibile: {device['rm']})")
            if device['rm'] == true and device['type'] == "disk":
                for partition in device.get('children', []):
                    if partition['type'] == "part":
                        usb_device = f"/dev/{partition['name']}"
                        break
                if usb_device:
                    break

        if not usb_device:
            print("Nessuna chiavetta USB trovata")
            return None

        print(f"Chiavetta USB trovata: {usb_device}")

        # Crea punto di mount se non esiste
        if not os.path.exists(mount_point):
            print(f"Creazione punto di mount: {mount_point}")
            subprocess.run(["sudo", "mkdir", "-p", mount_point], check=True)

        # Monta il dispositivo
        if not os.path.ismount(mount_point):
            print(f"Montaggio dispositivo in: {mount_point}")
            subprocess.run(["sudo", "mount", usb_device, mount_point], check=True)
        else:
            print("Smontaggio punto di mount precedente...")
            subprocess.run(["sudo", "umount", mount_point], check=True)
            print(f"Montaggio nuovo dispositivo in: {mount_point}")
            subprocess.run(["sudo", "mount", usb_device, mount_point], check=True)

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
