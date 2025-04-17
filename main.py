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
RC_PORT = 9090  # Porta per il controllo RC di VLC

# Configurazione IP
MASTER_IP = "192.168.2.1"
SLAVE_IPS = ["192.168.2.2"]

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

    def connect_rc(self):
        """Connette al controllo RC di VLC"""
        try:
            time.sleep(1)  # Attendi che VLC sia pronto
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

    def pause(self):
        """Mette in pausa il video"""
        self.send_rc_command("pause")

    def prepare_video(self, video_path):
        """Prepara il video ma lo mantiene in pausa"""
        with self.lock:
            self.video_path = video_path
            if self.video_process:
                self.stop_video()
            self.video_process = play_fullscreen_video(video_path)
            if self.connect_rc():
                time.sleep(0.5)
                self.pause()  # Metti subito in pausa
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

    def sync_playback(self):
        """Sincronizza la riproduzione"""
        self.send_rc_command("seek 0")
        time.sleep(0.1)
        self.send_rc_command("play")

    def check_video_running(self):
        """Verifica se il video è in esecuzione"""
        return self.video_process and self.video_process.poll() is None

def find_first_video(mount_point=MOUNT_POINT):
    """Trova il primo video nella prima chiavetta USB disponibile"""
    try:
        # Verifica che il punto di mount esista
        if not os.path.exists(mount_point):
            print(f"Directory {mount_point} non trovata")
            return None

        # Cerca tutte le directory nella cartella di mount
        mounted_devices = []
        for device in os.listdir(mount_point):
            device_path = os.path.join(mount_point, device)

            # Verifica che sia una directory
            if os.path.isdir(device_path):
                mounted_devices.append(device_path)

        if not mounted_devices:
            print("Nessuna chiavetta USB trovata")
            return None

        video_extensions = ['.mp4', '.avi', '.mkv', '.mov']
        print(f"Dispositivi trovati: {mounted_devices}")

        # Cerca in ogni dispositivo montato
        for device_path in mounted_devices:
            print(f"Cerco video in: {device_path}")

            # Cerca ricorsivamente nella directory
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

                # Preparazione sincronizzata
                s.sendall(b"PREPARE_SYNC")
                if s.recv(1024).decode().strip() == "READY":
                    print("Slave pronto, preparo countdown...")
                    time.sleep(1)

                    # Countdown sincronizzato
                    for i in range(3, 0, -1):
                        s.sendall(f"COUNTDOWN_{i}".encode())
                        response = s.recv(1024).decode().strip()
                        print(f"Sincronizzazione tra {i}...")
                        time.sleep(1)

                    # Avvio sincronizzato
                    s.sendall(SYNC_COMMAND.encode())
                    if s.recv(1024).decode().strip() == "VIDEO_STARTED":
                        print("Sincronizzazione completata")
                        controller.sync_playback()

                        # Loop di controllo
                        while controller.running:
                            try:
                                s.sendall(b"CHECK_SYNC")
                                response = s.recv(1024).decode().strip()
                                if response == "NEED_SYNC":
                                    print("Risincronizzazione...")
                                    s.sendall(b"SYNC_NOW")
                                    time.sleep(0.1)
                                    controller.sync_playback()
                                time.sleep(1)
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

    # Prepara il video in pausa
    print("Preparo il video...")
    controller.prepare_video(video_file)

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

    # Il video partirà tramite sync_playback nel thread di connessione
    try:
        while controller.running:
            if not controller.check_video_running():
                print("Riavvio video dopo crash")
                controller.prepare_video(video_file)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interruzione richiesta")
        controller.stop_video()

def main_slave():
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
                                    controller.prepare_video(video_file)
                                    conn.sendall(b"READY")
                                else:
                                    conn.sendall(b"NO_VIDEO")
                                    break

                            elif message.startswith("COUNTDOWN_"):
                                print(f"Sincronizzazione tra {message[-1]}...")
                                conn.sendall(b"COUNTDOWN_OK")

                            elif message == SYNC_COMMAND:
                                controller.sync_playback()
                                conn.sendall(b"VIDEO_STARTED")

                            elif message == "CHECK_SYNC":
                                if not controller.check_video_running():
                                    conn.sendall(b"NEED_SYNC")
                                else:
                                    conn.sendall(b"IN_SYNC")

                            elif message == "SYNC_NOW":
                                controller.sync_playback()

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

        # Verifica connessione ethernet
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
