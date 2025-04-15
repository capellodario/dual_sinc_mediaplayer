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

    #command = ["mpv", "--fullscreen", "--loop", "--vo=rpi", "--hwdec=rpi", video_path] # Prova prima 'rpi' con hwdec
    command = ["mpv", "--fullscreen", "--loop", "--vo=gpu", video_path]       # Se 'rpi' non va, prova 'gpu'
    # command = ["mpv", "--fullscreen", "--loop", "--vo=dispmanx", video_path]  # Un'altra opzione senza X
    print(f"Avvio video a schermo intero con mpv (loop attivato, vo=rpi, hwdec=rpi): {command}")
    process = subprocess.Popen(command)
    return process

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
    ethernet_connected = is_ethernet_connected()

    if hostname == MASTER_HOSTNAME:
        # Comportamento da Master
        if ethernet_connected:
            print("(Master) Cavo Ethernet rilevato. Avvio server e attendo che gli slave siano pronti.")
            # Avvia il server slave anche sul master
            threading.Thread(target=start_server, args=(True,)).start()
            time.sleep(1) # Breve attesa per l'avvio del server locale

            slave_ips = {}
            for slave_hostname in SLAVE_HOSTNAMES:
                try:
                    slave_ips[slave_hostname] = socket.gethostbyname(slave_hostname)
                except socket.gaierror:
                    print(f"(Master) Impossibile risolvere l'IP per {slave_hostname}")

            ready_slaves = {}
            for slave_hostname, slave_ip in slave_ips.items():
                print(f"(Master) Attendo che {slave_hostname} ({slave_ip}) sia pronto...")
                start_time = time.time()
                while time.time() - start_time < SLAVE_READY_TIMEOUT:
                    if check_slave_ready(slave_ip):
                        print(f"(Master) {slave_hostname} è pronto.")
                        ready_slaves[slave_hostname] = slave_ip
                        break
                    time.sleep(SLAVE_CHECK_INTERVAL)
                else:
                    print(f"(Master) Timeout: {slave_hostname} non è diventato pronto entro {SLAVE_READY_TIMEOUT} secondi.")

            video_file_master = find_first_video()
            if video_file_master:
                print(f"(Master) Trovato video: {video_file_master}")
                # Avvia la riproduzione sul master
                master_process = play_fullscreen_video(video_file_master)

                # Invia il comando di sincronizzazione agli slave pronti
                print("(Master) Invio comando di sincronizzazione agli slave pronti.")
                for slave_ip in ready_slaves.values():
                    send_sync_command(slave_ip)

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
        else:
            video_file_master = find_first_video()
            if video_file_master:
                print("(Master) Nessun cavo Ethernet rilevato. Riproduzione locale.")
                master_process = play_fullscreen_video(video_file_master)
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
            print(f"(Slave - {hostname}) Cavo Ethernet rilevato. Avvio server e ricerca video locale.")
            threading.Thread(target=start_server, args=(False,)).start()
            video_file_slave = find_first_video()
            if video_file_slave:
                print(f"(Slave - {hostname}) Video trovato: {video_file_slave}. In attesa del comando SYNC.")
                # Il percorso del video è ora pronto
            else:
                print(f"(Slave - {hostname}) Nessun video trovato localmente. In attesa del comando SYNC (ma non potrò riprodurre).")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print(f"(Slave - {hostname}) Server slave terminato.")
        else:
            video_file_slave = find_first_video()
            if video_file_slave:
                print(f"(Slave - {hostname}) Nessun cavo Ethernet rilevato. Riproduzione video locale.")
                slave_process = play_fullscreen_video(video_file_slave)
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    if slave_process:
                        slave_process.terminate()
                        slave_process.wait()
                    print(f"(Slave - {hostname}) Processo video terminato.")
            else:
                print(f"(Slave - {hostname}) Nessun video da riprodurre localmente.")

