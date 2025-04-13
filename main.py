import subprocess
import time
import os
import glob
import socket
import signal  # Importa il modulo signal
import sys

# --- Configurazione (Master) ---
MOUNT_POINT = "/media/muchomas/"
SLAVE_IP_ADDRESS = "192.168.1.101"
SLAVE_PORT = 12345  # Porta su cui lo Slave ascolterà
DEBUG_MODE = True  # Imposta a False per abilitare l'attesa dello Slave
SEND_TO_SLAVE = False  # Imposta a False per disabilitare l'invio del comando allo Slave
VLC_OUTPUT_MODULE = "wl_dmabuf"  # Usa il modulo Wayland che funziona

master_process = None  # Variabile globale per tenere traccia del processo VLC

def find_first_video(base_path):
    """Cerca il primo file video trovato in tutte le sottocartelle del percorso base, escludendo i file macOS metadata."""
    for root, _, files in os.walk(base_path):
        valid_video_files = sorted([f for f in files if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')) and not f.startswith('._')])
        if valid_video_files:
            return os.path.join(root, valid_video_files[0])
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
            "--vout=wl_dmabuf",  # Forza l'output Wayland
            "--loop",
            "--fullscreen",
            "--no-osd",  # Disabilita l'OSD per nascondere la scritta
            "--codec=h264",    # Forza il codec software h264
            video_path,
        ]
        print(f"[DEBUG MASTER] Comando VLC che verrà eseguito: {vlc_command}")
        global master_process
        master_process = subprocess.Popen(vlc_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return master_process
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

def signal_handler(sig, frame):
    """Gestisce il segnale di interruzione (Ctrl+C)."""
    print("\n[DEBUG MASTER] Ricevuto segnale di interruzione, terminazione di VLC...")
    global master_process
    if master_process:
        master_process.terminate()
        master_process.wait()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)  # Registra il gestore per Ctrl+C

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
            play_video_master(master_video_path)

            if master_process:
                print("[DEBUG MASTER] Processo VLC Master avviato (in loop, Ctrl+C per terminare).")

                if SEND_TO_SLAVE:
                    print("[DEBUG MASTER] Invio comando di avvio allo Slave...")
                    trigger_slave()
                else:
                    print("[DEBUG MASTER] Invio comando allo Slave disabilitato.")

                try:
                    while True:
                        time.sleep(1)  # Mantieni lo script in esecuzione per intercettare Ctrl+C
                except KeyboardInterrupt:
                    # Questa eccezione verrà catturata dal signal handler
                    pass
            else:
                print("[DEBUG MASTER] Errore nell'avvio del processo VLC sul Master.")
        else:
            print("[DEBUG MASTER] Nessun file video trovato per il Master.")
    else:
        print("[DEBUG MASTER] Chiavetta USB non trovata sul Master.")