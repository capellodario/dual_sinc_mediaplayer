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
SLAVE_HOSTNAMES = ["nomehost-slave1"]  # Ridotto a un solo slave
ETHERNET_INTERFACE = "eth0"
MOUNT_POINT = "/media/muchomas"
SYNC_COMMAND = "PLAY_SYNC"
SLAVE_READY_RESPONSE = "READY"
SLAVE_CHECK_INTERVAL = 2
SLAVE_READY_TIMEOUT = 10

# Configurazione IP
MASTER_IP = "192.168.2.1"
SLAVE_IPS = ["192.168.2.2"]

def get_hostname():
    return socket.gethostname()

def is_ethernet_connected(interface=ETHERNET_INTERFACE):
    try:
        with open(f"/sys/class/net/{interface}/carrier") as f:
            if int(f.read().strip()) == 1:
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
    try:
        hostname = get_hostname()
        ip = MASTER_IP if hostname == MASTER_HOSTNAME else SLAVE_IPS[0]

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
    command = [
        "cvlc",
        "--fullscreen",
        "--no-osd",
        "--play-and-exit",
        "--aout=pipewire",
        video_path
    ]
    print(f"Avvio riproduzione: {video_path}")
    return subprocess.Popen(command)

class VideoController:
    def __init__(self, is_master=False):
        self.is_master = is_master
        self.video_process = None
        self.running = True
        self.connected_slaves = set()
        self.lock = threading.Lock()

    def start_video(self, video_path):
        with self.lock:
            if self.video_process:
                self.video_process.terminate()
                self.video_process.wait()
            self.video_process = play_fullscreen_video(video_path)
            return self.video_process

    def stop_video(self):
        with self.lock:
            if self.video_process:
                self.video_process.terminate()
                self.video_process.wait()
                self.video_process = None

def handle_master_connection(controller, slave_ip):
    print(f"Tentativo di connessione allo slave {slave_ip}")
    while controller.running:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((slave_ip, CONTROL_PORT))
                print(f"Connesso allo slave {slave_ip}")
                controller.connected_slaves.add(slave_ip)

                while controller.running:
                    try:
                        s.sendall(SYNC_COMMAND.encode())
                        response = s.recv(1024).decode().strip()

                        if response == "VIDEO_STARTED":
                            print(f"Slave {slave_ip} sincronizzato")

                        time.sleep(1)

                    except socket.error as e:
                        print(f"Errore comunicazione con slave: {e}")
                        break

        except Exception as e:
            print(f"Errore connessione con slave {slave_ip}: {e}")
            controller.connected_slaves.discard(slave_ip)
            time.sleep(5)

def handle_slave_connection(controller, conn, addr):
    print(f"Gestione connessione da {addr}")
    try:
        while controller.running:
            data = conn.recv(1024)
            if not data:
                print(f"Connessione chiusa da {addr}")
                break

            message = data.decode().strip()
            print(f"Ricevuto comando: {message}")

            if message == SYNC_COMMAND:
                video_file = find_first_video()
                if video_file:
                    print(f"Avvio video su richiesta: {video_file}")
                    controller.start_video(video_file)
                    conn.sendall(b"VIDEO_STARTED")
                else:
                    print("Nessun video trovato")
                    conn.sendall(b"NO_VIDEO")

    except Exception as e:
        print(f"Errore nella gestione connessione slave: {e}")
    finally:
        conn.close()
        print(f"Connessione chiusa con {addr}")

def main_master():
    controller = VideoController(is_master=True)
    video_file = find_first_video()

    if not video_file:
        print("Nessun video trovato")
        return

    thread = threading.Thread(
        target=handle_master_connection,
        args=(controller, SLAVE_IPS[0])
    )
    thread.daemon = True
    thread.start()

    while controller.running:
        try:
            print("Avvio nuovo ciclo di riproduzione")

            wait_start = time.time()
            while len(controller.connected_slaves) == 0:
                if time.time() - wait_start > 30:
                    print("Timeout attesa slave, procedo comunque")
                    break
                print("In attesa connessione slave...")
                time.sleep(1)

            process = controller.start_video(video_file)
            process.wait()
            time.sleep(1)

        except KeyboardInterrupt:
            print("Interruzione richiesta")
            break
        except Exception as e:
            print(f"Errore nel loop principale: {e}")
            time.sleep(1)

def main_slave():
    controller = VideoController(is_master=False)
    print("Avvio slave in modalità ascolto...")

    while controller.running:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('0.0.0.0', CONTROL_PORT))
                server.listen(1)
                print("Slave in ascolto...")

                while controller.running:
                    try:
                        conn, addr = server.accept()
                        print(f"Connessione accettata da {addr}")
                        handle_slave_connection(controller, conn, addr)
                    except Exception as e:
                        print(f"Errore accettazione connessione: {e}")
                        time.sleep(1)

        except Exception as e:
            print(f"Errore server slave: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Attesa iniziale per permettere al sistema di inizializzarsi
    time.sleep(5)
    hostname = get_hostname()

    # Setup rete
    if not setup_network():
        print("Errore nella configurazione della rete")
        exit(1)

    # Attesa connessione ethernet
    print("Attendo che la connessione ethernet sia attiva...")
    for _ in range(30):
        if is_ethernet_connected():
            print("Connessione ethernet stabilita")
            break
        time.sleep(1)
    else:
        print("Impossibile stabilire la connessione ethernet")
        exit(1)

    # Avvio appropriato in base al ruolo
    if hostname == MASTER_HOSTNAME:
        main_master()
    elif hostname in SLAVE_HOSTNAMES:
        main_slave()
    else:
        print(f"Hostname non riconosciuto: {hostname}")
