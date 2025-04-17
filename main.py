import subprocess
import time
import os
import glob
import socket
import netifaces as ni
import threading

# Configurazione comune
CONTROL_PORT = 12345
MASTER_HOSTNAME = "nomehost-master"
SLAVE_HOSTNAMES = ["nomehost-slave1", "nomehost-slave2"]
ETHERNET_INTERFACE = "eth0"
MOUNT_POINT = "/media/muchomas"
SYNC_COMMAND = "PLAY_SYNC"
SLAVE_READY_RESPONSE = "READY"
SLAVE_CHECK_INTERVAL = 2  # Secondi tra i tentativi di ping degli slave
SLAVE_READY_TIMEOUT = 10  # Secondi totali da attendere per ogni slave

# Nuova configurazione IP
MASTER_IP = "192.168.2.1"
SLAVE_IPS = ["192.168.2.2"]

def get_hostname():
    return socket.gethostname()

def is_ethernet_connected(interface=ETHERNET_INTERFACE):
    try:
        with open(f"/sys/class/net/{interface}/carrier") as f:
            if int(f.read().strip()) == 1:
                # Verifica anche la connettività IP
                if get_hostname() == MASTER_HOSTNAME:
                    target_ip = SLAVE_IPS[0]
                else:
                    target_ip = MASTER_IP

                response = os.system(f"ping -c 1 -W 1 {target_ip} > /dev/null 2>&1")
                return response == 0
        return False
    except Exception as e:
        print(f"Errore verifica ethernet: {e}")
        return False

def setup_network():
    """Configura la rete con IP statici"""
    try:
        hostname = get_hostname()
        if hostname == MASTER_HOSTNAME:
            ip = MASTER_IP
        else:
            ip = SLAVE_IPS[0]

        os.system(f"sudo ip link set {ETHERNET_INTERFACE} down")
        os.system(f"sudo ip addr flush dev {ETHERNET_INTERFACE}")
        os.system(f"sudo ip addr add {ip}/24 dev {ETHERNET_INTERFACE}")
        os.system(f"sudo ip link set {ETHERNET_INTERFACE} up")
        print(f"IP configurato: {ip}")
        return True
    except Exception as e:
        print(f"Errore configurazione rete: {e}")
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
        """
        Riproduce un video a schermo intero in loop utilizzando cvlc.

        Args:
            video_path (str): Il percorso completo del file video.
        """
        command = [
            "cvlc",
            "--fullscreen",
            "--loop",
            "--no-osd",  # Aggiunta per nascondere l'OSD
            "--aout=pipewire",
            video_path
        ]

        print(f"Avvio riproduzione a schermo intero in loop con cvlc: {video_path}")

        try:
            # Esegui cvlc come un processo in background
            process = subprocess.Popen(command)
            print("Riproduzione con cvlc avviata. Premi Ctrl+C per interrompere.")

            # Mantieni lo script in esecuzione per consentire la riproduzione di cvlc
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nInterruzione richiesta. Terminando cvlc...")
            # Termina il processo cvlc se l'utente preme Ctrl+C
            if 'process' in locals() and process.poll() is None:
                process.terminate()
                process.wait()
            print("cvlc terminato.")
        except FileNotFoundError:
            print("Errore: Il comando 'cvlc' non è stato trovato. Assicurati che VLC sia installato e che 'cvlc' sia nel PATH.")
        except Exception as e:
            print(f"Si è verificato un errore: {e}")

def send_sync_command(slave_ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((slave_ip, CONTROL_PORT))
            s.sendall(SYNC_COMMAND.encode())
        print(f"Comando SYNC inviato a {slave_ip}")
        return True
    except ConnectionRefusedError:
        print(f"Connessione rifiutata da {slave_ip}. Assicurati che lo script slave sia in esecuzione.")
        return False
    except Exception as e:
        print(f"Errore durante l'invio del comando a {slave_ip}: {e}")
        return False

def check_slave_ready(slave_ip):
    """Verifica se lo slave è in ascolto sulla porta di controllo."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # Timeout breve per non bloccare troppo
            s.connect((slave_ip, CONTROL_PORT))
            s.sendall(b"ARE_YOU_READY")
            response = s.recv(1024).decode().strip()
            return response == SLAVE_READY_RESPONSE
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False
    return False

def handle_connection(conn, addr, is_master):
    print(f"Connesso da {addr}")
    while True:
        data = conn.recv(1024)
        if not data:
            break
        message = data.decode().strip()
        print(f"({'Master' if is_master else 'Slave'}) Ricevuto: {message}")
        if message == SYNC_COMMAND:
            if not is_master:
                video_file = find_first_video()
                if video_file:
                    play_fullscreen_video(video_file)
                else:
                    print(f"(Slave - {get_hostname()}) Nessun video trovato localmente per la riproduzione sincronizzata.")
        elif message == "ARE_YOU_READY":
            conn.sendall(SLAVE_READY_RESPONSE.encode())
        conn.sendall(b"OK")

def start_server(is_master):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', CONTROL_PORT))
        s.listen()
        print(f"({'Master' if is_master else 'Slave'}) In ascolto sulla porta {CONTROL_PORT}...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_connection, args=(conn, addr, is_master)).start()

if __name__ == "__main__":
    time.sleep(5)
    hostname = get_hostname()

    # Configura la rete prima di tutto
    if not setup_network():
        print("Errore nella configurazione della rete")
        exit(1)

    # Attendi che la rete sia pronta
    print("Attendo che la connessione ethernet sia attiva...")
    for _ in range(30):  # 30 secondi di tentativi
        if is_ethernet_connected():
            print("Connessione ethernet stabilita")
            break
        time.sleep(1)
    else:
        print("Impossibile stabilire la connessione ethernet")
        exit(1)

    if hostname == MASTER_HOSTNAME:
        # Comportamento Master
        print("(Master) Avvio server e attendo che gli slave siano pronti.")
        threading.Thread(target=start_server, args=(True,)).start()
        time.sleep(1)

        ready_slaves = {}
        for slave_ip in SLAVE_IPS:
            print(f"(Master) Attendo che lo slave {slave_ip} sia pronto...")
            start_time = time.time()
            while time.time() - start_time < SLAVE_READY_TIMEOUT:
                if check_slave_ready(slave_ip):
                    print(f"(Master) Slave {slave_ip} è pronto.")
                    ready_slaves[slave_ip] = slave_ip
                    break
                time.sleep(SLAVE_CHECK_INTERVAL)
            else:
                print(f"(Master) Timeout: {slave_ip} non è pronto")

        video_file_master = find_first_video()
        if video_file_master:
            print(f"(Master) Trovato video: {video_file_master}")
            # Avvia la riproduzione sul master
            master_process = play_fullscreen_video(video_file_master)

            # Invia il comando di sincronizzazione agli slave pronti
            for slave_ip in ready_slaves.values():
                send_sync_command(slave_ip)

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                if master_process:
                    master_process.terminate()
                    master_process.wait()
                print("(Master) Processo terminato.")
        else:
            print("(Master) Nessun video da riprodurre.")

    elif hostname in SLAVE_HOSTNAMES:
        # Comportamento Slave
        print(f"(Slave - {hostname}) Avvio server e ricerca video locale.")
        threading.Thread(target=start_server, args=(False,)).start()

        video_file_slave = find_first_video()
        if video_file_slave:
            print(f"(Slave - {hostname}) Video trovato: {video_file_slave}. In attesa del comando SYNC.")
        else:
            print(f"(Slave - {hostname}) Nessun video trovato localmente.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"(Slave - {hostname}) Server terminato.")
