import subprocess
import time
import os
import glob
import socket
import netifaces as ni
import argparse

# Configurazione comune
CONTROL_PORT = 12345
MASTER_HOSTNAME = "nomehost-master"
SLAVE_HOSTNAMES = ["nomehost-slave1", "nomehost-slave2"]
ETHERNET_INTERFACE = "eth0"
MOUNT_POINT = "/media/muchomas"

def get_hostname():
    return socket.gethostname()

def is_ethernet_connected(interface=ETHERNET_INTERFACE):
    try:
        iface_info = ni.ifaddresses(interface)
        return ni.AF_INET in iface_info
    except ValueError:
        return False
    except Exception as e:
        print(f"Errore durante la verifica della connessione Ethernet: {e}")
        return False

def find_first_video(mount_point=MOUNT_POINT):
    chiavette = glob.glob(f"{mount_point}/rasp_key*")
    if chiavette:
        first_chiavetta = chiavette[0]
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov']
        for root, _, files in os.walk(first_chiavetta):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    return os.path.join(root, file)
        print(f"Nessun file video trovato nella chiavetta: {first_chiavetta}")
        return None
    else:
        print("Nessuna chiavetta USB 'rasp_key*' trovata.")
        return None

def play_fullscreen_video(video_path):
    """Riproduce il video a schermo intero con mpv in loop."""
    command = ["mpv", "--fullscreen", "--loop", video_path]
    print(f"Avvio video a schermo intero con mpv (loop attivato): {command}")
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process

def send_play_command(slave_ip, video_path):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((slave_ip, CONTROL_PORT))
            s.sendall(f"PLAY:{video_path}".encode())
        print(f"Comando PLAY inviato a {slave_ip}: {video_path}")
        return True
    except ConnectionRefusedError:
        print(f"Connessione rifiutata da {slave_ip}. Assicurati che lo script slave sia in esecuzione.")
        return False
    except Exception as e:
        print(f"Errore durante l'invio del comando a {slave_ip}: {e}")
        return False

def handle_connection(conn, addr, is_master):
    print(f"Connesso da {addr}")
    while True:
        data = conn.recv(1024)
        if not data:
            break
        message = data.decode().strip()
        print(f"({'Master' if is_master else 'Slave'}) Ricevuto: {message}")
        if message.startswith("PLAY:"):
            video_path = message[5:]
            video_file = find_first_video()
            if video_file:
                play_fullscreen_video(video_file)
            else:
                print(f"({'Master' if is_master else 'Slave'}) Nessun video trovato localmente.")
        conn.sendall(b"OK")

def start_server(is_master):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', CONTROL_PORT))
        s.listen()
        print(f"({'Master' if is_master else 'Slave'}) In ascolto sulla porta {CONTROL_PORT}...")
        while True:
            conn, addr = s.accept()
            handle_connection(conn, addr, is_master)

if __name__ == "__main__":
    time.sleep(5)
    hostname = get_hostname()
    ethernet_connected = is_ethernet_connected()
    video_file = find_first_video()

    if hostname == MASTER_HOSTNAME:
        # Comportamento da Master
        if video_file:
            print(f"(Master) Trovato video: {video_file}")
            master_process = play_fullscreen_video(video_file)

            if ethernet_connected:
                print("(Master) Cavo Ethernet rilevato. Invio comandi agli slave.")
                import threading
                slave_thread = threading.Thread(target=start_server, args=(True,))
                slave_thread.daemon = True
                slave_thread.start()

                for slave_hostname in SLAVE_HOSTNAMES:
                    try:
                        slave_ip = socket.gethostbyname(slave_hostname)
                        send_play_command(slave_ip, video_file)
                    except socket.gaierror:
                        print(f"(Master) Impossibile risolvere l'IP per {slave_hostname}")

            else:
                print("(Master) Nessun cavo Ethernet rilevato. Riproduzione solo locale.")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                if master_process:
                    master_process.terminate()
                    master_process.wait()
                print("(Master) Processo video terminato.")
        else:
            print("(Master) Nessun video da riprodurre.")

    elif hostname in SLAVE_HOSTNAMES:
        # Comportamento da Slave
        if ethernet_connected:
            print(f"(Slave - {hostname}) Cavo Ethernet rilevato. Avvio server in ascolto...")
            start_server(False)
        else:
            if video_file:
                print(f"(Slave - {hostname}) Nessun cavo Ethernet rilevato. Riproduzione video locale.")
                play_fullscreen_video(video_file)
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print(f"(Slave - {hostname}) Processo video terminato.")
            else:
                print(f"(Slave - {hostname}) Nessun video da riprodurre localmente.")

    else:
        # Ruolo sconosciuto
        if video_file:
            print(f"(Sconosciuto - {hostname}) Hostname non riconosciuto. Riproduzione locale.")
            play_fullscreen_video(video_file)
            try:
                while True:
                    time.sleep(1)
                except KeyboardInterrupt:
                    print(f"(Sconosciuto - {hostname}) Processo video terminato.")
            else:
                print(f"(Sconosciuto - {hostname}) Hostname non riconosciuto e nessun video trovato.")
        else:
            print(f"(Sconosciuto - {hostname}) Hostname non riconosciuto e nessun video trovato.")