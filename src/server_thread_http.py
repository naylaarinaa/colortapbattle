from socket import *
import socket, threading, sys, logging, signal
from http import HttpServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    required_players = min(max(int(sys.argv[1]), 2), 10) if len(sys.argv) > 1 else 2
except Exception:
    required_players = 2

httpserver = HttpServer(required_players=required_players)

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        super().__init__(daemon=True)
        self.connection, self.address = connection, address

    def run(self):
        self.connection.settimeout(1.0)
        rcv = ""
        try:
            while True:
                try:
                    data = self.connection.recv(4096)
                    if not data: break
                    rcv += data.decode('utf-8', errors='ignore')
                    if "\r\n\r\n" in rcv:
                        logging.info(f"Request from {self.address}: {rcv.splitlines()[0]}")
                        hasil = httpserver.proses(rcv)
                        self.connection.sendall(hasil)
                        break
                except socket.timeout:
                    continue
                except OSError as e:
                    logging.error(f"OSError with {self.address}: {e}")
                    break
        except Exception as e:
            logging.error(f"Error processing {self.address}: {e}")
        finally:
            self.connection.close()
            logging.info(f"Connection with {self.address} closed")

class Server(threading.Thread):
    def __init__(self):
        super().__init__(daemon=False)
        self.the_clients, self.my_socket = [], socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True

    def run(self):
        try:
            self.my_socket.bind(('0.0.0.0', 8889))
            self.my_socket.listen(5)
            self.my_socket.settimeout(1.0)
            logging.info("Color Tap Battle Server started on 0.0.0.0:8889")
            logging.info(f"Required players to start: {required_players}")
            while self.running:
                try:
                    self.connection, self.client_address = self.my_socket.accept()
                    logging.info(f"New connection from {self.client_address}")
                    clt = ProcessTheClient(self.connection, self.client_address)
                    clt.start()
                    self.the_clients.append(clt)
                    self.the_clients = [t for t in self.the_clients if t.is_alive()]
                except socket.timeout:
                    continue
                except OSError as e:
                    if self.running: logging.error(f"Socket error: {e}")
                    break
        except Exception as e:
            logging.error(f"Server error: {e}")
        finally:
            self.cleanup()

    def stop(self):
        logging.info("Stopping server...")
        self.running = False
        for t in self.the_clients: t.join(timeout=1.0)
        self.cleanup()

    def cleanup(self):
        try:
            self.my_socket.close()
            logging.info("Server socket closed")
        except Exception:
            pass

server = None

def signal_handler(sig, frame):
    print("\n🛑 Received interrupt signal (Ctrl+C)\nShutting down server gracefully...")
    global server
    if server:
        server.stop()
        server.join(timeout=3.0)
    print("✅ Server stopped. Goodbye!")
    sys.exit(0)

def main():
    global server
    signal.signal(signal.SIGINT, signal_handler)
    print("Starting Color Tap Battle Server...")
    print(f"Required players to start: {required_players}")
    print("Press Ctrl+C to stop the server")
    try:
        server = Server()
        server.start()
        while server.is_alive():
            server.join(timeout=1.0)
    except KeyboardInterrupt:
        if server: server.stop()
    except Exception as e:
        logging.error(f"Main thread error: {e}")
        if server: server.stop()
    finally:
        print("Main thread exiting...")

if __name__ == "__main__":
    main()