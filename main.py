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

# Configurazione timeout per fallback
ETHERNET_CHECK_TIMEOUT = 30  # Secondi per verificare ethernet
SLAVE_CONNECTION_TIMEOUT = 30  # Secondi per attendere connessione slave

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

def play_standalone_video(video_path):
    """Riproduce un video a schermo intero in loop senza controllo RC (modalità standalone)"""
    command = [
        "cvlc",
        "--fullscreen",
        "--no-osd",
        "--loop",
        "--no-video-title",
        "--no-video-title-show",
        "--aout=pipewire",
        "--quiet",
        video_path
    ]
    print(f"Avvio riproduzione standalone in loop: {video_path}")
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
        self.standalone_mode = False

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

    def start_video(self, video_path, standalone=False):
        with self.lock:
            self.video_path = video_path
            self.standalone_mode = standalone
            if self.video_process:
                self.stop_video()

            if standalone:
                print("Avvio video in modalità standalone (senza sync)")
                self.video_process = play_standalone_video(video_path)
            else:
                self.video_process = play_fullscreen_video(video_path)
                if self.connect_rc():
                    time.sleep(0.5)  # Breve attesa per stabilizzazione
                    return self.video_process
                return None

            return self.video_process

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
        if not self.standalone_mode:
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

            # Verifica che sia una directory e un dispositivo rimovibile
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
                # Ordina i file per nome per avere un ordine consistente
                for file in sorted(files):
                    # Debug logging
                    print(f"Controllo file: {file}")

                    # Verifica esplicita per file che iniziano con ._
                    if file.startswith('._'):
                        print(f"Ignorato file nascosto: {file}")
                        continue

                    # Verifica estensione
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        video_path = os.path.join(root, file)
                        print(f"Video valido trovato: {video_path}")
                        return video_path
                    else:
                        print(f"File non video: {file}")

        print("Nessun video valido trovato nelle chiavette USB")
        return None

    except Exception as e:
        print(f"Errore durante la ricerca del video: {str(e)}")
        return None

def handle_master_connection(controller, slave_ip):
    """Gestisce la connessione master-slave"""
    print(f"Tentativo connessione a slave: {slave_ip}")
    connection_established = False

    while controller.running:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((slave_ip, CONTROL_PORT))
                print(f"Connesso a slave: {slave_ip}")
                controller.connected_slaves.add(slave_ip)
                connection_established = True

                # Sincronizzazione iniziale
                s.sendall(b"PREPARE_SYNC")
                if s.recv(1024).decode().strip() == "READY":
                    time.sleep(2)  # Attesa per stabilizzazione
                    s.sendall(SYNC_COMMAND.encode())
                    if s.recv(1024).decode().strip() == "VIDEO_STARTED":
                        print("Sincronizzazione iniziale completata")
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
            if not connection_established:
                break  # Esci se non è mai riuscito a connettersi
            time.sleep(5)

def main_master():
    """Funzione principale del master"""
    controller = VideoController(is_master=True)
    video_file = find_first_video()

    if not video_file:
        print("Nessun video trovato")
        return

    print("Verifica connessione ethernet per sync...")
    ethernet_ok = is_ethernet_connected()

    if ethernet_ok:
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
        slave_connected = False

        while len(controller.connected_slaves) == 0:
            if time.time() - wait_start > SLAVE_CONNECTION_TIMEOUT:
                print("Timeout attesa slave, avvio modalità standalone")
                break
            print("Attendo connessione slave...")
            time.sleep(1)

        if len(controller.connected_slaves) > 0:
            slave_connected = True
            print("Slave connesso, modalità sincronizzata")

    # Determina la modalità di avvio
    standalone_mode = not ethernet_ok or len(controller.connected_slaves) == 0

    if standalone_mode:
        print("MODALITÀ STANDALONE: Avvio video senza sincronizzazione")
    else:
        print("MODALITÀ SYNC: Avvio video con sincronizzazione")

    # Avvia il video e mantieni il processo
    try:
        process = controller.start_video(video_file, standalone=standalone_mode)
        while controller.running:
            if not controller.check_video_running():
                print("Riavvio video dopo crash")
                process = controller.start_video(video_file, standalone=standalone_mode)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interruzione richiesta")
        controller.stop_video()

def main_slave():
    """Funzione principale dello slave"""
    controller = VideoController(is_master=False)
    print("Avvio slave...")

    # Verifica se ethernet è disponibile
    ethernet_ok = is_ethernet_connected()

    if not ethernet_ok:
        print("MODALITÀ STANDALONE: Ethernet non disponibile, avvio video senza sync")
        video_file = find_first_video()
        if video_file:
            try:
                process = controller.start_video(video_file, standalone=True)
                while controller.running:
                    if not controller.check_video_running():
                        print("Riavvio video dopo crash")
                        process = controller.start_video(video_file, standalone=True)
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Interruzione richiesta")
                controller.stop_video()
        else:
            print("Nessun video trovato per modalità standalone")
        return

    print("Ethernet OK, modalità sync - Slave in ascolto...")

    # Timeout per verificare se arriva una connessione dal master
    server_timeout = time.time() + SLAVE_CONNECTION_TIMEOUT
    fallback_to_standalone = True

    while controller.running and time.time() < server_timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.settimeout(5)  # Timeout per accept
                server.bind(('0.0.0.0', CONTROL_PORT))
                server.listen(1)
                print("Slave in ascolto...")

                try:
                    conn, addr = server.accept()
                    if addr[0] != MASTER_IP:
                        conn.close()
                        continue

                    fallback_to_standalone = False  # Connessione ricevuta
                    print(f"Connessione master accettata: {addr}")

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

                except socket.timeout:
                    print("Timeout attesa connessione master")
                    continue

        except Exception as e:
            print(f"Errore server: {e}")
            time.sleep(1)

    # Se non è arrivata nessuna connessione, avvia modalità standalone
    if fallback_to_standalone:
        print("MODALITÀ STANDALONE: Nessuna connessione dal master, avvio video autonomo")
        video_file = find_first_video()
        if video_file:
            try:
                process = controller.start_video(video_file, standalone=True)
                while controller.running:
                    if not controller.check_video_running():
                        print("Riavvio video dopo crash")
                        process = controller.start_video(video_file, standalone=True)
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Interruzione richiesta")
                controller.stop_video()

if __name__ == "__main__":
    try:
        print(f"Avvio su host: {get_hostname()}")

        # Verifica connessione ethernet (con timeout ridotto)
        print("Verifica connessione ethernet...")
        ethernet_connected = False
        for attempt in range(ETHERNET_CHECK_TIMEOUT):
            print(f"Tentativo {attempt + 1}/{ETHERNET_CHECK_TIMEOUT}")
            if is_ethernet_connected():
                print("Connessione ethernet OK")
                ethernet_connected = True
                break
            time.sleep(1)

        if not ethernet_connected:
            print("Connessione ethernet non disponibile - modalità standalone attivata")

        # Avvia in base al ruolo (anche senza ethernet)
        hostname = get_hostname()
        if hostname == MASTER_HOSTNAME:
            main_master()
        elif hostname in SLAVE_HOSTNAMES:
            main_slave()
        else:
            print(f"Hostname non riconosciuto: {hostname}")
            # Anche per hostname non riconosciuti, prova modalità standalone
            print("Tentativo avvio modalità standalone...")
            video_file = find_first_video()
            if video_file:
                controller = VideoController(is_master=False)
                try:
                    process = controller.start_video(video_file, standalone=True)
                    print("Video avviato in modalità standalone")
                    while controller.running:
                        if not controller.check_video_running():
                            print("Riavvio video dopo crash")
                            process = controller.start_video(video_file, standalone=True)
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("Interruzione richiesta")
                    controller.stop_video()
            else:
                print("Nessun video trovato")

    except KeyboardInterrupt:
        print("\nInterruzione manuale del programma")
    except Exception as e:
        print(f"Errore fatale: {e}")
