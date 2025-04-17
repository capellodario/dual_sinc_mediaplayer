import subprocess
import time
import os
import socket
import threading
import ntplib

# Configurazione comune
CONTROL_PORT = 12345
MASTER_HOSTNAME = "nomehost-master"
SLAVE_HOSTNAMES = ["nomehost-slave1"]
ETHERNET_INTERFACE = "eth0"
MOUNT_POINT = "/media/muchomas"
SYNC_COMMAND = "PLAY_SYNC"
RC_PORT = 9090
NTP_SERVER = "pool.ntp.org"

# Configurazione IP
MASTER_IP = "192.168.2.1"
SLAVE_IPS = ["192.168.2.2"]

def sync_system_time():
    """Sincronizza l'orologio di sistema con NTP"""
    try:
        ntp_client = ntplib.NTPClient()
        response = ntp_client.request(NTP_SERVER)
        return True
    except:
        return False

def get_hostname():
    return socket.gethostname()

def is_ethernet_connected():
    """Verifica la connessione ethernet usando NetworkManager"""
    try:
        result = subprocess.run(['nmcli', '-g', 'GENERAL.STATE', 'con', 'show', 'dual-sync'],
                              capture_output=True, text=True)
        if "activated" in result.stdout.lower():
            target_ip = SLAVE_IPS[0] if get_hostname() == MASTER_HOSTNAME else MASTER_IP
            response = os.system(f"ping -I {ETHERNET_INTERFACE} -c 1 -W 1 {target_ip} > /dev/null 2>&1")
            return response == 0
        return False
    except Exception as e:
        print(f"Errore verifica ethernet: {e}")
        return False

def play_fullscreen_video(video_path):
    """Riproduce un video a schermo intero in loop con interfaccia RC"""
    command = [
        "cvlc",
        "--fullscreen",
        "--no-osd",
        "--loop",
        "--no-video-title",
        "--no-video-title-show",
        "--aout=pipewire",
        "--quiet",
        "--intf", "rc",
        "--rc-host", f"localhost:{RC_PORT}",
        "--clock-jitter=0",
        "--clock-synchro=0",
        "--audio-desync=0",
        "--sout-mux-caching=0",
        "--network-caching=0",
        "--live-caching=0",
        "--file-caching=0",
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
        self.rc_socket = None
        self.sync_ready = threading.Event()
        self.video_path = None
        self.last_sync_time = 0
        self.sync_interval = 2  # Sincronizza ogni 2 secondi
        self.playback_position = 0

    def connect_rc(self):
        """Connette al controllo RC di VLC"""
        try:
            time.sleep(1)
            self.rc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.rc_socket.connect(('localhost', RC_PORT))
            print("Connesso al controllo RC di VLC")
            return True
        except Exception as e:
            print(f"Errore connessione RC: {e}")
            return False

    def send_rc_command(self, command):
        """Invia comando a VLC"""
        try:
            if self.rc_socket:
                self.rc_socket.send(f"{command}\n".encode())
                return True
        except Exception as e:
            print(f"Errore invio comando RC: {e}")
        return False

    def precise_sync_playback(self):
        """Sincronizzazione precisa della riproduzione"""
        self.send_rc_command("pause")
        time.sleep(0.05)
        self.send_rc_command("seek 0")
        time.sleep(0.05)
        self.send_rc_command("frame")
        time.sleep(0.05)

        # Sincronizzazione temporizzata
        start_time = time.time()
        while time.time() - start_time < 0.1:
            pass

        self.send_rc_command("play")
        self.last_sync_time = time.time()
        self.playback_position = 0

    def start_video(self, video_path):
        with self.lock:
            self.video_path = video_path
            if self.video_process:
                self.stop_video()
            self.video_process = play_fullscreen_video(video_path)
            if self.connect_rc():
                time.sleep(0.5)
                return self.video_process
            return None

    def stop_video(self):
        with self.lock:
            if self.rc_socket:
                try:
                    self.rc_socket.close()
                except:
                    pass
                self.rc_socket = None
            if self.video_process:
                self.video_process.terminate()
                try:
                    self.video_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.video_process.kill()
                self.video_process = None

    def need_sync(self):
        current_time = time.time()
        return current_time - self.last_sync_time >= self.sync_interval

    def check_video_running(self):
        """Verifica se il video è in esecuzione"""
        return self.video_process and self.video_process.poll() is None

def find_first_video(mount_point=MOUNT_POINT):
    """Trova il primo video nella prima chiavetta USB disponibile"""
    try:
        if not os.path.exists(mount_point):
            print(f"Directory {mount_point} non trovata")
            return None

        mounted_devices = [os.path.join(mount_point, d) for d in os.listdir(mount_point)
                         if os.path.isdir(os.path.join(mount_point, d))]

        if not mounted_devices:
            print("Nessuna chiavetta USB trovata")
            return None

        video_extensions = ['.mp4', '.avi', '.mkv', '.mov']
        print(f"Dispositivi trovati: {mounted_devices}")

        for device_path in mounted_devices:
            print(f"Cerco video in: {device_path}")
            for root, _, files in os.walk(device_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        video_path = os.path.join(root, file)
                        print(f"Video trovato: {video_path}")
                        return video_path

        print("Nessun video trovato nelle chiavette USB")
        return None

    except Exception as e:
        print(f"Errore durante la ricerca del video: {e}")
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

                s.sendall(b"PREPARE_SYNC")
                if s.recv(1024).decode().strip() == "READY":
                    time.sleep(1)
                    s.sendall(SYNC_COMMAND.encode())
                    if s.recv(1024).decode().strip() == "VIDEO_STARTED":
                        print("Sincronizzazione iniziale completata")
                        controller.precise_sync_playback()

                        while controller.running:
                            try:
                                if controller.need_sync():
                                    s.sendall(b"SYNC_NOW")
                                    time.sleep(0.05)
                                    controller.precise_sync_playback()
                                else:
                                    s.sendall(b"CHECK_SYNC")
                                    response = s.recv(1024).decode().strip()
                                    if response == "NEED_SYNC":
                                        controller.precise_sync_playback()
                                time.sleep(0.2)
                            except:
                                break

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

    thread = threading.Thread(
        target=handle_master_connection,
        args=(controller, SLAVE_IPS[0])
    )
    thread.daemon = True
    thread.start()

    print("Attendo che lo slave sia pronto...")
    wait_start = time.time()
    while len(controller.connected_slaves) == 0:
        if time.time() - wait_start > 30:
            print("Timeout attesa slave, procedo comunque")
            break
        time.sleep(1)

    try:
        print("Avvio riproduzione in loop")
        process = controller.start_video(video_file)
        while controller.running:
            if not controller.check_video_running():
                print("Riavvio video dopo crash")
                process = controller.start_video(video_file)
            time.sleep(0.5)
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
                    if addr[0] != MASTER_IP:
                        conn.close()
                        continue

                    print(f"Connessione accettata: {addr}")
                    try:
                        while True:
                            data = conn.recv(1024)
                            if not data:
                                break

                            message = data.decode().strip()
                            if message == "PREPARE_SYNC":
                                video_file = find_first_video()
                                if video_file:
                                    controller.start_video(video_file)
                                    conn.sendall(b"READY")
                                else:
                                    conn.sendall(b"NO_VIDEO")
                                    break

                            elif message == SYNC_COMMAND:
                                controller.precise_sync_playback()
                                conn.sendall(b"VIDEO_STARTED")

                            elif message == "SYNC_NOW":
                                controller.precise_sync_playback()
                                conn.sendall(b"SYNCED")

                            elif message == "CHECK_SYNC":
                                if controller.need_sync() or not controller.check_video_running():
                                    conn.sendall(b"NEED_SYNC")
                                else:
                                    conn.sendall(b"IN_SYNC")

                    except Exception as e:
                        print(f"Errore gestione connessione: {e}")
                    finally:
                        conn.close()

        except Exception as e:
            print(f"Errore server: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        print(f"Avvio su host: {get_hostname()}")

        # Sincronizza l'orologio di sistema
        if sync_system_time():
            print("Orologio di sistema sincronizzato")
        else:
            print("Impossibile sincronizzare l'orologio di sistema")

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

        hostname = get_hostname()
        if hostname == MASTER_HOSTNAME:
            main_master()
        elif hostname in SLAVE_HOSTNAMES:
            main_slave()
        else:
            print(f"Hostname non riconosciuto: {hostname}")

    except KeyboardInterrupt:
        print("\nInterruzione manuale del programma")
    except Exception as e:
        print(f"Errore fatale: {e}")
