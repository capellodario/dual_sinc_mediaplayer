import subprocess
import time
import os
import glob
import socket

# --- Configurazione (Master) ---
MOUNT_POINT = "/media/pi/"
MASTER_VIDEO_FILE = "master_video.mp4"
AUDIO_FILE = "audio.wav"
SLAVE_IP_ADDRESS = "192.168.1.101"
SLAVE_PORT = 12345  # Porta su cui lo Slave ascolterà
DEBUG_MODE = True  # Imposta a False per abilitare l'attesa dello Slave

def find_media_path(base_path, filename):
    """Cerca il file specificato in tutte le sottocartelle del percorso base."""
    for root, _, files in os.walk(base_path):
        if filename in files:
            return os.path.join(root, filename)
    return None

def check_slave_ready():
    """Tenta di connettersi allo Slave per verificare se è pronto."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # Timeout di 5 secondi per la connessione
            s.connect((SLAVE_IP_ADDRESS, SLAVE_PORT))
            return True
    except (socket.error, socket.timeout):
        return False

def play_video_master(video_path, audio_path):
    """Riproduce il video e l'audio in loop sul Master."""
    vlc_command = [
        "cvlc",
        "--loop",
        "--fullscreen",
        video_path,
        "--audio-file",
        audio_path,
        "vlc://quit"
    ]
    return subprocess.Popen(vlc_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def trigger_slave():
    """Invia un comando SSH per avviare la riproduzione sul Slave."""
    ssh_command = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "pi@" + SLAVE_IP_ADDRESS,
        f"bash /home/pi/start_slave_video.sh"  # Assumendo che lo script sia in /home/pi
    ]
    subprocess.run(ssh_command, check=True)

if __name__ == "__main__":
    time.sleep(10)  # Attendi il montaggio dell'USB

    usb_path = glob.glob(f"{MOUNT_POINT}*")[0] if glob.glob(f"{MOUNT_POINT}*") else None

    if usb_path:
        master_video_path = find_media_path(usb_path, MASTER_VIDEO_FILE)
        audio_path = find_media_path(usb_path, AUDIO_FILE)

        if master_video_path and audio_path:
            if not DEBUG_MODE:
                print("Attesa che lo Slave sia pronto...")
                while not check_slave_ready():
                    print("Slave non ancora pronto, riprovo tra 2 secondi...")
                    time.sleep(2)
                print("Slave pronto!")

            print("Avvio video e audio sul Master...")
            master_process = play_video_master(master_video_path, audio_path)
            time.sleep(1)  # Piccolo ritardo per dare tempo al Master di avviarsi
            print("Invio comando di avvio allo Slave...")
            try:
                trigger_slave()
                print("Comando inviato allo Slave.")
                try:
                    master_process.wait()  # Mantieni in esecuzione fino all'interruzione
                except KeyboardInterrupt:
                    print("Interruzione, terminazione del Master...")
                    master_process.terminate()
                    master_process.wait()
            except subprocess.CalledProcessError as e:
                print(f"Errore nell'invio del comando allo Slave: {e}")
        else:
            print("File video o audio per il Master non trovati.")
    else:
        print("Chiavetta USB non trovata sul Master.")