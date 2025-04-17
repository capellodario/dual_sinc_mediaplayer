import subprocess
import time
import os
import glob
import socket
import threading

# Configurazione comune
CONTROL_PORT = 12345
MASTER_HOSTNAME = "nomehost-master"
SLAVE_HOSTNAMES = ["nomehost-slave1"]  # Solo uno slave
ETHERNET_INTERFACE = "eth0"
MOUNT_POINT = "/media/muchomas"
SYNC_COMMAND = "PLAY_SYNC"

# Configurazione IP
MASTER_IP = "192.168.2.1"
SLAVE_IPS = ["192.168.2.2"]

def get_hostname():
    return socket.gethostname()

def is_ethernet_connected():
    """Verifica la connessione ethernet usando NetworkManager"""
    try:
        # Verifica lo stato della connessione dual-sync
        result = subprocess.run(['nmcli', '-g', 'GENERAL.STATE', 'con', 'show', 'dual-sync'],
                              capture_output=True, text=True)

        if "activated" in result.stdout.lower():
            # Verifica ping
            target_ip = SLAVE_IPS[0] if get_hostname() == MASTER_HOSTNAME else MASTER_IP
            response = os.system(f"ping -I {ETHERNET_INTERFACE} -c 1 -W 1 {target_ip} > /dev/null 2>&1")
            return response == 0
        return False
    except Exception as e:
        print(f"Errore verifica ethernet: {e}")
        return False

def play_fullscreen_video(video_path):
    """Riproduce un video a schermo intero in loop"""
    command = [
        "cvlc",
        "--fullscreen",
        "--no-osd",
        "--loop",  # Aggiunto loop direttamente qui
        "--no-video-title",
        "--no-video-title-show",
        "--aout=pipewire",
        "--quiet",
        video_path
    ]
    print(f"Avvio riproduzione in loop: {video_path}")
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

def find_first_video(mount_point=MOUNT_POINT):
    """Trova il primo video nella chiavetta USB"""
    chiavette = glob.glob(f"{mount_point}/rasp_key*")
    if chiavette:
        first_chiavetta = chiavette[0]
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov']
        for root, _, files in os.walk(first_chiavetta):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    return os.path.join(root, file)
        print(f"Nessun video trovato in: {first_chiavetta}")
        return None
    print("Nessuna chiavetta USB 'rasp_key*' trovata")
    return None

def handle_master_connection(controller, slave_ip):
    """Gestisce la connessione master-slave"""
    print(f"Tentativo connessione a slave: {slave_ip}")
    while controller.running:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((slave_ip, CONTROL_PORT))
                print(f"Connesso a slave: {slave_ip}")
                controller.connected_slaves.add(slave_ip)

                # Invia solo una volta il comando di sincronizzazione
                s.sendall(SYNC_COMMAND.encode())
                response = s.recv(1024).decode().strip()
                if response == "VIDEO_STARTED":
                    print(f"Slave {slave_ip} sincronizzato e in loop")

                    # Mantieni la connessione aperta
                    while controller.running:
                        time.sleep(1)

        except Exception as e:
            print(f"Errore connessione slave: {e}")
            controller.connected_slaves.discard(slave_ip)
            time.sleep(5)

def main_master():
    """Funzione principale del master"""
    controller = VideoController(is_master=True)
    video_file = find_first_video()

    if not video_file:
        print("Nessun video trovato")
        return

    # Avvia thread per la connessione allo slave
    thread = threading.Thread(
        target=handle_master_connection,
        args=(controller, SLAVE_IPS[0])
    )
    thread.daemon = True
    thread.start()

    # Attendi che lo slave sia connesso
    print("Attendo che lo slave sia pronto...")
    wait_start = time.time()
    while len(controller.connected_slaves) == 0:
        if time.time() - wait_start > 30:
            print("Timeout attesa slave, procedo comunque")
            break
        print("Attendo connessione slave...")
        time.sleep(1)

    # Avvia il video in loop e mantienilo in esecuzione
    try:
        print("Avvio riproduzione in loop")
        process = controller.start_video(video_file)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interruzione richiesta")
        controller.stop_video()

def main_slave():
    """Funzione principale dello slave"""
    controller = VideoController(is_master=False)
    print("Avvio slave in ascolto...")

    while controller.running:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('0.0.0.0', CONTROL_PORT))
                server.listen(1)
                print("Slave in ascolto...")

                while controller.running:
                    conn, addr = server.accept()
                    print(f"Connessione accettata: {addr}")

                    data = conn.recv(1024)
                    if data:
                        message = data.decode().strip()
                        if message == SYNC_COMMAND:
                            video_file = find_first_video()
                            if video_file:
                                print(f"Avvio video in loop: {video_file}")
                                controller.start_video(video_file)
                                conn.sendall(b"VIDEO_STARTED")

                                # Mantieni la connessione aperta
                                while True:
                                    time.sleep(1)
                            else:
                                conn.sendall(b"NO_VIDEO")

        except Exception as e:
            print(f"Errore server: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print(f"Avvio su host: {get_hostname()}")

    # Attendi che la rete sia pronta
    print("Verifica connessione ethernet...")
    for attempt in range(30):
        print(f"Tentativo {attempt + 1}/30")
        if is_ethernet_connected():
            print("Connessione ethernet OK")
            break
        time.sleep(1)
    else:
        print("Impossibile stabilire connessione ethernet")
        exit(1)

    # Avvia in base al ruolo
    if get_hostname() == MASTER_HOSTNAME:
        main_master()
    elif get_hostname() in SLAVE_HOSTNAMES:
        main_slave()
    else:
        print(f"Hostname non riconosciuto: {get_hostname()}")
