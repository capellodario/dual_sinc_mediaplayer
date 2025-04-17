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
    """Riproduce un video a schermo intero con transizioni più fluide"""
    command = [
        "cvlc",
        "--fullscreen",
        "--no-osd",
        "--no-video-title",
        "--no-video-title-show",
        "--no-quiet",
        "--play-and-exit",
        "--no-keyboard-events",
        "--no-mouse-events",
        "--aout=pipewire",
        "--vout=xcb_x11",  # o "vout=x11" se xcb_x11 non funziona
        "--no-snapshot-preview",
        "--no-overlay",
        "--no-qt-privacy-ask",
        "--qt-minimal-view",
        "--no-qt-system-tray",
        video_path
    ]
    print(f"Avvio riproduzione: {video_path}")

    # Imposta DISPLAY se non è già impostato
    env = os.environ.copy()
    if 'DISPLAY' not in env:
        env['DISPLAY'] = ':0'

    return subprocess.Popen(command, env=env)

class VideoController:
    def __init__(self, is_master=False):
        self.is_master = is_master
        self.video_process = None
        self.running = True
        self.connected_slaves = set()
        self.lock = threading.Lock()
        self.is_playing = False

        # Preparazione ambiente X11
        os.system("xset -dpms")     # Disabilita power management
        os.system("xset s off")     # Disabilita screensaver
        os.system("xset s noblank") # Disabilita screen blanking

    def start_video(self, video_path):
        with self.lock:
            if self.is_playing and self.video_process and self.video_process.poll() is None:
                print("Video già in riproduzione")
                return None

            if self.video_process:
                try:
                    self.video_process.terminate()
                    self.video_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.video_process.kill()
                    self.video_process.wait()
                self.video_process = None

            time.sleep(0.1)

            print(f"Avvio riproduzione: {video_path}")
            self.video_process = play_fullscreen_video(video_path)
            self.is_playing = True
            return self.video_process

    def stop_video(self):
        with self.lock:
            if self.video_process:
                try:
                    self.video_process.terminate()
                    self.video_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.video_process.kill()
                    self.video_process.wait()
                self.video_process = None
            self.is_playing = False
            time.sleep(0.1)

    def __del__(self):
        # Ripristina le impostazioni X11 alla chiusura
        os.system("xset +dpms")
        os.system("xset s on")
        os.system("xset s blank")

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

                # Invia il comando SYNC solo una volta all'inizio
                s.sendall(SYNC_COMMAND.encode())
                response = s.recv(1024).decode().strip()
                if response == "VIDEO_STARTED":
                    print(f"Slave {slave_ip} sincronizzato")

                # Mantieni la connessione aperta
                while controller.running:
                    try:
                        s.sendall(b"HEARTBEAT")
                        response = s.recv(1024).decode().strip()
                        time.sleep(1)
                    except socket.error as e:
                        print(f"Errore comunicazione: {e}")
                        break

        except Exception as e:
            print(f"Errore connessione slave: {e}")
            controller.connected_slaves.discard(slave_ip)
            time.sleep(5)

def handle_slave_connection(controller, conn, addr):
    """Gestisce la connessione lato slave"""
    print(f"Connessione da: {addr}")
    try:
        while controller.running:
            data = conn.recv(1024)
            if not data:
                break

            message = data.decode().strip()

            if message == SYNC_COMMAND and not controller.is_playing:
                video_file = find_first_video()
                if video_file:
                    print(f"Avvio video: {video_file}")
                    controller.start_video(video_file)
                    conn.sendall(b"VIDEO_STARTED")
                else:
                    conn.sendall(b"NO_VIDEO")
            elif message == "HEARTBEAT":
                conn.sendall(b"ALIVE")

                if controller.video_process and controller.video_process.poll() is not None:
                    print("Video terminato, riavvio...")
                    controller.is_playing = False
                    video_file = find_first_video()
                    if video_file:
                        controller.start_video(video_file)

    except Exception as e:
        print(f"Errore connessione: {e}")
    finally:
        conn.close()
        controller.is_playing = False
        print(f"Connessione chiusa: {addr}")

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

    while controller.running:
        try:
            print("Avvio ciclo riproduzione")

            wait_start = time.time()
            while len(controller.connected_slaves) == 0:
                if time.time() - wait_start > 30:
                    print("Timeout attesa slave, procedo")
                    break
                print("Attendo connessione slave...")
                time.sleep(1)

            process = controller.start_video(video_file)
            process.wait()
            time.sleep(1)

        except KeyboardInterrupt:
            print("Interruzione richiesta")
            break
        except Exception as e:
            print(f"Errore: {e}")
            time.sleep(1)

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
                    try:
                        conn, addr = server.accept()
                        print(f"Connessione accettata: {addr}")
                        handle_slave_connection(controller, conn, addr)
                    except Exception as e:
                        print(f"Errore accettazione: {e}")
                        time.sleep(1)

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
