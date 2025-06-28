from socket import *
import socket
import threading
import time
import sys
import logging
import signal
from http import HttpServer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ambil jumlah pemain dari argumen, default 2, maksimal 10
if len(sys.argv) > 1:
    try:
        required_players = int(sys.argv[1])
        if required_players < 2:
            required_players = 2
        elif required_players > 10:
            required_players = 10
    except ValueError:
        required_players = 2
else:
    required_players = 2

httpserver = HttpServer(required_players=required_players)

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        self.running = True
        threading.Thread.__init__(self)
        self.daemon = True  # Important: daemon thread will exit when main exits

    def run(self):
        rcv = ""
        try:
            # Set socket timeout to allow checking self.running
            self.connection.settimeout(1.0)
            
            while self.running:
                try:
                    data = self.connection.recv(4096)
                    if data:
                        d = data.decode('utf-8', errors='ignore')
                        rcv = rcv + d
                        if "\r\n\r\n" in rcv:
                            logging.info("Request from client {}: {}".format(self.address, rcv.split('\r\n')[0]))
                            hasil = httpserver.proses(rcv)
                            
                            # Don't add extra \r\n\r\n - response already formatted
                            logging.info("Response to client {}: {} bytes".format(self.address, len(hasil)))
                            self.connection.sendall(hasil)
                            rcv = ""
                            self.connection.close()
                            break
                    else:
                        break
                except socket.timeout:
                    # Timeout allows checking self.running
                    continue
                except OSError as e:
                    logging.error("OSError with client {}: {}".format(self.address, e))
                    break
        except Exception as e:
            logging.error("Error processing client {}: {}".format(self.address, e))
        finally:
            try:
                self.connection.close()
            except:
                pass
            logging.info("Connection with client {} closed".format(self.address))

    def stop(self):
        """Gracefully stop the client thread"""
        self.running = False

class Server(threading.Thread):
    def __init__(self):
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True
        threading.Thread.__init__(self)
        self.daemon = False  # Main server thread should not be daemon

    def run(self):
        try:
            self.my_socket.bind(('0.0.0.0', 8889))
            self.my_socket.listen(5)
            # Set socket timeout to allow checking self.running
            self.my_socket.settimeout(1.0)
            
            logging.info("Color Tap Battle Server started on 0.0.0.0:8889")
            logging.info("Required players to start: {}".format(required_players))
            logging.info("Server ready to accept connections...")
            
            while self.running:
                try:
                    self.connection, self.client_address = self.my_socket.accept()
                    logging.info("New connection from {}".format(self.client_address))

                    clt = ProcessTheClient(self.connection, self.client_address)
                    clt.start()
                    self.the_clients.append(clt)
                    
                    # Clean up finished threads
                    self.cleanup_finished_threads()
                    
                except socket.timeout:
                    # Timeout allows checking self.running
                    continue
                except OSError as e:
                    if self.running:
                        logging.error("Socket error: {}".format(e))
                    break
        except Exception as e:
            logging.error("Server error: {}".format(e))
        finally:
            self.cleanup()

    def cleanup_finished_threads(self):
        """Remove finished client threads from the list"""
        self.the_clients = [t for t in self.the_clients if t.is_alive()]

    def stop(self):
        """Gracefully stop the server"""
        logging.info("Stopping server...")
        self.running = False
        
        # Stop all client threads
        for client_thread in self.the_clients:
            client_thread.stop()
        
        # Wait for all client threads to finish (with timeout)
        for client_thread in self.the_clients:
            client_thread.join(timeout=1.0)
        
        self.cleanup()

    def cleanup(self):
        """Clean up server resources"""
        try:
            self.my_socket.close()
            logging.info("Server socket closed")
        except:
            pass

# Global server instance
server = None

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    print("\n🛑 Received interrupt signal (Ctrl+C)")
    print("Shutting down server gracefully...")
    
    global server
    if server:
        server.stop()
        server.join(timeout=3.0)  # Wait up to 3 seconds for server to stop
    
    print("✅ Server stopped. Goodbye!")
    sys.exit(0)

def main():
    global server
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Starting Color Tap Battle Server...")
    print(f"Required players to start: {required_players}")
    print("Press Ctrl+C to stop the server")
    
    try:
        server = Server()
        server.start()
        
        # Keep main thread alive and responsive to signals
        while server.is_alive():
            server.join(timeout=1.0)  # Check every 1 second
            
    except KeyboardInterrupt:
        # This should be caught by signal_handler, but just in case
        print("\n🛑 Keyboard interrupt received")
        if server:
            server.stop()
    except Exception as e:
        logging.error("Main thread error: {}".format(e))
        if server:
            server.stop()
    finally:
        print("Main thread exiting...")

if __name__ == "__main__":
    main()