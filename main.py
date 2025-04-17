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
    try:
        ntp_client = ntplib.NTPClient()
        response = ntp_client.request(NTP_SERVER)
        return True
    except:
        return False

def get_hostname():
    return socket.gethostname()

def is_ethernet_connected():
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
        "--drop-late-frames",
        "--skip-frames",
        "--quiet-synchro",
        "--no-keyboard-events",
        "--no-mouse-events",
        video_path
    ]
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
        self.sync_interval = 2
        self.playback_position = 0
        self.restart_attempts = 0
        self.max_restart_attempts = 3
        self.last_restart_time = 0
        self.restart_cooldown = 10

    def connect_rc(self):
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
        try:
            if self.rc_socket:
                self.rc_socket.send(f"{command}\n".encode())
                return True
        except Exception as e:
            print(f"Errore invio comando RC: {e}")
        return False

    def precise_sync_playback(self):
        self.send_rc_command("pause")
        time.sleep(0.05)
        self.send_rc_command("seek 0")
        time.sleep(0.05)
        self.send_rc_command("frame")
        time.sleep(0.05)

        start_time = time.time()
        while time.time() - start_time < 0.1:
            pass

        self.send_rc_command("play")
        self.last_sync_time = time.time()
        self.playback_position = 0

    def start_video(self, video_path):
        with self.lock:
            current_time = time.time()
            if current_time - self.last_restart_time < self.restart_cooldown:
                print("Attendo cooldown prima di riavviare...")
                time.sleep(self.restart_cooldown)

            self.video_path = video_path
            if self.video_process:
                self.stop_video()

            try:
                self.video_process = play_fullscreen_video(video_path)
                if self.connect_rc():
                    time.sleep(1)
                    self.send_rc_command("play")
                    self.restart_attempts = 0
                    self.last_restart_time = current_time
                    return self.video_process
            except Exception as e:
                print(f"Errore avvio video: {e}")
                self.restart_attempts += 1
                if self.restart_attempts >= self.max_restart_attempts:
                    print("Troppi tentativi di riavvio falliti")
                    time.sleep(self.restart_cooldown)
                    self.restart_attempts = 0
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
        try:
            if not self.video_process:
                return False

            if self.video_process.poll() is not None:
                return False

            if self.rc_socket:
                try:
                    self.send_rc_command("get_time")
                    return True
                except:
                    return False

            return True
        except:
            return False

def find_first_video(mount_point=MOUNT_POINT):
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
    controller = VideoController(is_master=False)
    print("Avvio slave in ascolto...")

    def restart_video():
        video_file = find_first_video()
        if video_file:
            return controller.start_video(video_file)
        return None

    initial_video = find_first_video()
    if initial_video:
        controller.start_video(initial_video)

    while controller.running:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('0.0.0.0', CONTROL_PORT))
                server.listen(1)
                print("Slave in ascolto...")

                def monitor_video():
                    while controller.running:
                        if not controller.check_video_running():
                            print("Video non in esecuzione, riavvio...")
                            restart_video()
                        time.sleep(1)

                monitor_thread = threading.Thread(target=monitor_video)
                monitor_thread.daemon = True
                monitor_thread.start()

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
                                if not controller.check_video_running():
                                    if restart_video():
                                        conn.sendall(b"READY")
                                    else:
                                        conn.sendall(b"NO_VIDEO")
                                        break
                                else:
                                    conn.sendall(b"READY")

                            elif message == SYNC_COMMAND:
                                if not controller.check_video_running():
                                    restart_video()
                                controller.precise_sync_playback()
                                conn.sendall(b"VIDEO_STARTED")

                            elif message == "SYNC_NOW":
                                if not controller.check_video_running():
                                    restart_video()
                                controller.precise_sync_playback()
                                conn.sendall(b"SYNCED")

                            elif message == "CHECK_SYNC":
                                if not controller.check_video_running():
                                    restart_video()
                                    conn.sendall(b"NEED_SYNC")
                                elif controller.need_sync():
                                    conn.sendall(b"NEED_SYNC")
                                else:
                                    conn.sendall(b"IN_SYNC")

                    except Exception as e:
                        print(f"Errore gestione connessione: {e}")
                        restart_video()
                    finally:
                        conn.close()

        except Exception as e:
            print(f"Errore server: {e}")
            restart_video()
            time.sleep(5)

if __name__ == "__main__":
    try:
        print(f"Avvio su host: {get_hostname()}")

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
