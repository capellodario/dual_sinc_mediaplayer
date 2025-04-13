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
VLC_OUTPUT_MODULE = "wl_dmabuf"  # Usa il modulo Wayland che funziona

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
            "--no-osd",  # Disabilita l'OSD per nascondere la scritta
            video_path,
            "vlc://quit"
        ]
        print(f"[DEBUG MASTER] Comando VLC che verrà eseguito: {vlc_command}")
        process = subprocess.Popen(vlc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            print(f"[DEBUG MASTER] Errore da VLC: {stderr.decode()}")
        return process
    return None

def trigger_slave():
    """Invia un comando SSH per avviare la riproduzione sul Slave."""
    ssh_command = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "pi@" + SLAVE_IP_ADDRESS,
        f"bash /home/pi/start_slave_video.sh"  # Assumendo che lo script sia in /home/pi
    ]
    print(f"[DEBUG MASTER] Comando SSH per lo Slave: {ssh_command}")
    try:
        subprocess.run(ssh_command, check=True)
        print("[DEBUG MASTER] Comando SSH inviato con successo.")
    except subprocess.CalledProcessError as e:
        print(f"[DEBUG MASTER] Errore nell'invio del comando allo Slave: {e}")

if __name__ == "__main__":
    time.sleep(10)  # Attendi il montaggio dell'USB

    usb_path = glob.glob(f"{MOUNT_POINT}*")[0] if glob.glob(f"{MOUNT_POINT}*") else None

    if usb_path:
        master_video_path = find_first_video(usb_path)
        print(f"[DEBUG MASTER] Percorso video trovato: {master_video_path}")

        if master_video_path:
            if not DEBUG_MODE:
                print("[DEBUG MASTER] Attesa che lo Slave sia pronto...")
                while not check_slave_ready():
                    print("[DEBUG MASTER] Slave non ancora pronto, riprovo tra 2 secondi...")
                    time.sleep(2)
                print("[DEBUG MASTER] Slave pronto!")
            else:
                print("[DEBUG MASTER] Modalità DEBUG attiva: salto l'attesa dello Slave.")

            print("[DEBUG MASTER] Avvio video sul Master...")
            master_process = play_video_master(master_video_path)

            if master_process:
                print("[DEBUG MASTER] Processo VLC Master avviato.")
                time.sleep(1)  # Piccolo ritardo per dare tempo al Master di avviarsi

                if SEND_TO_SLAVE:
                    print("[DEBUG MASTER] Invio comando di avvio allo Slave...")
                    trigger_slave()
                else:
                    print("[DEBUG MASTER] Invio comando allo Slave disabilitato.")

                try:
                    master_process.wait()  # Mantieni in esecuzione fino all'interruzione
                    print("[DEBUG MASTER] Processo VLC Master terminato.")
                except KeyboardInterrupt:
                    print("[DEBUG MASTER] Interruzione, terminazione del Master...")
                    master_process.terminate()
                    master_process.wait()
            else:
                print("[DEBUG MASTER] Errore nell'avvio del processo VLC sul Master.")
        else:
            print("[DEBUG MASTER] Nessun file video trovato per il Master.")
    else:
        print("[DEBUG MASTER] Chiavetta USB non trovata sul Master.")