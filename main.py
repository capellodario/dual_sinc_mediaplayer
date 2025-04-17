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

def play_fullscreen_video(video_path, is_master=False):
    """
    Riproduce un video a schermo intero in loop utilizzando cvlc e monitora la riproduzione.
    Ritorna un oggetto processo per il controllo.
    """
    command = [
        "cvlc",
        "--fullscreen",
        "--loop",
        "--no-osd",
        "--aout=pipewire",
        "--play-and-exit",  # Importante per sapere quando il video finisce
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
            self.video_process = play_fullscreen_video(video_path, self.is_master)

    def stop_video(self):
        with self.lock:
            if self.video_process:
                self.video_process.terminate()
                self.video_process.wait()
                self.video_process = None

def handle_master_connection(controller, slave_ip):
    """Gestisce la connessione persistente con uno slave."""
    while controller.running:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((slave_ip, CONTROL_PORT))
                print(f"Connesso allo slave {slave_ip}")
                controller.connected_slaves.add(slave_ip)

                while controller.running:
                    # Controlla lo stato dello slave
                    s.sendall(b"STATUS")
                    response = s.recv(1024).decode().strip()

                    if response == "READY_FOR_SYNC":
                        # Invia comando di sincronizzazione
                        s.sendall(SYNC_COMMAND.encode())

                    time.sleep(1)  # Intervallo di polling

        except Exception as e:
            print(f"Errore connessione con slave {slave_ip}: {e}")
            controller.connected_slaves.discard(slave_ip)
            time.sleep(5)  # Attendi prima di ritentare

def handle_slave_connection(controller, conn, addr):
    """Gestisce la connessione persistente sul lato slave."""
    try:
        while controller.running:
            data = conn.recv(1024)
            if not data:
                break

            message = data.decode().strip()

            if message == "STATUS":
                conn.sendall(b"READY_FOR_SYNC")

            elif message == SYNC_COMMAND:
                video_file = find_first_video()
                if video_file:
                    controller.start_video(video_file)
                    conn.sendall(b"VIDEO_STARTED")
                else:
                    conn.sendall(b"NO_VIDEO")

    except Exception as e:
        print(f"Errore nella connessione slave: {e}")
    finally:
        conn.close()

def main_master():
    controller = VideoController(is_master=True)

    # Avvia thread di monitoraggio per ogni slave
    slave_threads = []
    for slave_ip in SLAVE_IPS:
        thread = threading.Thread(
            target=handle_master_connection,
            args=(controller, slave_ip)
        )
        thread.daemon = True
        thread.start()
        slave_threads.append(thread)

    # Avvia il video master
    video_file = find_first_video()
    if video_file:
        while controller.running:
            controller.start_video(video_file)
            time.sleep(1)  # Breve pausa tra i loop

            # Monitora il processo video
            while controller.video_process.poll() is None:
                time.sleep(1)

            # Quando il video finisce, riavvia sincronizzato con gli slave
            print("Video loop completato, risincronizzazione...")

def main_slave():
    controller = VideoController(is_master=False)

    # Avvia server slave
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(('0.0.0.0', CONTROL_PORT))
        server.listen()
        print("Slave in ascolto...")

        while controller.running:
            conn, addr = server.accept()
            threading.Thread(
                target=handle_slave_connection,
                args=(controller, conn, addr)
            ).start()

if __name__ == "__main__":
    hostname = get_hostname()

    # Setup iniziale come prima...

    if hostname == MASTER_HOSTNAME:
        main_master()
    elif hostname in SLAVE_HOSTNAMES:
        main_slave()
