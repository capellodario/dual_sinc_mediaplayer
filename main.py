import time
import os
import glob
import socket
import signal
import sys
import subprocess

# --- Configurazione (Master) ---
MOUNT_POINT_MASTER = "/media/muchomas/" # Punto di mount della chiavetta USB del Master
SLAVE_IP_ADDRESS = "192.168.1.101"
SLAVE_PORT = 12345  # Porta su cui lo Slave ascolterà
DEBUG_MODE = True
SEND_TO_SLAVE = False
MASTER_VIDEO_PATH = None  # Variabile globale per il percorso del video Master
master_process = None

def find_first_video(base_path):
    """Cerca il primo file video trovato."""
    for root, _, files in os.walk(base_path):
        valid_video_files = sorted([f for f in files if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')) and not f.startswith('._')])
        if valid_video_files:
            return os.path.join(root, valid_video_files[0])
    return None

def check_slave_ready():
    """Tenta di connettersi allo Slave per verificare se è in ascolto."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((SLAVE_IP_ADDRESS, SLAVE_PORT))
            print("[DEBUG MASTER] Slave trovato e pronto.")
            return True
    except (socket.error, socket.timeout):
        print("[DEBUG MASTER] Impossibile connettersi allo Slave. Riprovo...")
        return False

def send_start_command_to_slave():
    """Invia un comando al Slave per avviare la riproduzione."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((SLAVE_IP_ADDRESS, SLAVE_PORT))
            s.sendall(b"START\n") # Invia un semplice comando
            print("[DEBUG MASTER] Comando 'START' inviato allo Slave.")
            return True
    except (socket.error, socket.timeout):
        print("[DEBUG MASTER] Errore nell'invio del comando allo Slave.")
        return False

def play_video_master(video_path):
    """Riproduce il video in loop a schermo intero sul Master con ffmpeg."""
    if video_path:
        ffmpeg_command = [
            "ffmpeg",
            "-re",
            "-i", video_path,
            "-vf", "format=pix_fmts=rgb565le",  # Usa il formato suggerito
            "-an",
            "-loop", "0",
            "-f", "fbdev", "/dev/fb0"
        ]

        
        print(f"[DEBUG MASTER] Comando FFmpeg Master: {ffmpeg_command}")
        global master_process
        master_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return master_process
    return None

def signal_handler(sig, frame):
    """Gestisce il segnale di interruzione."""
    print("\n[DEBUG MASTER] Ricevuto segnale di interruzione, terminazione...")
    global master_process
    if master_process:
        master_process.terminate()
        master_process.wait()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    time.sleep(10) # Attendi montaggio USB Master

    usb_path_master = glob.glob(f"{MOUNT_POINT_MASTER}*")[0] if glob.glob(f"{MOUNT_POINT_MASTER}*") else None

    if usb_path_master:
        MASTER_VIDEO_PATH = find_first_video(usb_path_master)
        print(f"[DEBUG MASTER] Video Master trovato: {MASTER_VIDEO_PATH}")
    else:
        print("[DEBUG MASTER] Chiavetta USB non trovata sul Master.")
        sys.exit(1)

    if not DEBUG_MODE and SEND_TO_SLAVE:
        print("[DEBUG MASTER] Attendo che lo Slave sia pronto...")
        while not check_slave_ready():
            time.sleep(2)

        print("[DEBUG MASTER] Invio comando di avvio allo Slave...")
        send_start_command_to_slave()
    elif SEND_TO_SLAVE:
        print("[DEBUG MASTER] Modalità DEBUG attiva o invio disabilitato: non attendo/invio allo Slave.")

    if MASTER_VIDEO_PATH:
        print("[DEBUG MASTER] Avvio video sul Master...")
        play_video_master(MASTER_VIDEO_PATH)
        if master_process:
            print("[DEBUG MASTER] Riproduzione Master avviata (Ctrl+C per terminare).")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("[DEBUG MASTER] Errore nell'avvio del video sul Master.")
    else:
        print("[DEBUG MASTER] Nessun video trovato per il Master.")

    print("[DEBUG MASTER] Script Master terminato.")