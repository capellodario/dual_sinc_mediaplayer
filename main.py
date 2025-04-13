import subprocess
import time
import os
import glob
import socket

# --- Configurazione (Master) ---
MOUNT_POINT = "/media/muchomas/"
SLAVE_IP_ADDRESS = "192.168.1.101"
SLAVE_PORT = 12345  # Porta su cui lo Slave ascolterà
DEBUG_MODE = True  # Imposta a False per abilitare l'attesa dello Slave
SEND_TO_SLAVE = False  # Imposta a False per disabilitare l'invio del comando allo Slave

def find_first_video(base_path):
    """Cerca il primo file video trovato in tutte le sottocartelle del percorso base."""
    for root, _, files in os.walk(base_path):
        for file in sorted(files):
            if file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                return os.path.join(root, file)
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

def play_video_master(video_path):
    """Riproduce il video in loop a schermo intero sul Master."""
    if video_path:
        vlc_command = [
            "cvlc",
            "--loop",
            "--fullscreen",
            video_path,
            "vlc://quit"
        ]
        return subprocess.Popen(vlc_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return None

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
        master_video_path = find_first_video(usb_path)

        if master_video_path:
            if not DEBUG_MODE:
                print("Attesa che lo Slave sia pronto...")
                while not check_slave_ready():
                    print("Slave non ancora pronto, riprovo tra 2 secondi...")
                    time.sleep(2)
                print("Slave pronto!")

            print(f"Avvio video sul Master: {master_video_path}")
            master_process = play_video_master(master_video_path)
            time.sleep(1)  # Piccolo ritardo per dare tempo al Master di avviarsi

            if SEND_TO_SLAVE:
                print("Invio comando di avvio allo Slave...")
                try:
                    trigger_slave()
                    print("Comando inviato allo Slave.")
                except subprocess.CalledProcessError as e:
                    print(f"Errore nell'invio del comando allo Slave: {e}")
            else:
                print("Invio comando allo Slave disabilitato.")

            try:
                if master_process:
                    master_process.wait()  # Mantieni in esecuzione fino all'interruzione
            except KeyboardInterrupt:
                print("Interruzione, terminazione del Master...")
                if master_process:
                    master_process.terminate()
                    master_process.wait()
        else:
            print("Nessun file video trovato per il Master.")
    else:
        print("Chiavetta USB non trovata sul Master.")