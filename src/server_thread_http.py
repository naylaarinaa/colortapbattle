from socket import *
import socket, threading, sys, logging, signal, argparse
from http import HttpServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_arguments():
    parser = argparse.ArgumentParser(description='Stroop Color Game Server')
    parser.add_argument('--port', type=int, default=8889, help='Server port (default: 8889)')
    parser.add_argument('--redis-host', default='127.0.0.1', help='Redis host (default: 127.0.0.1)')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis port (default: 6379)')
    parser.add_argument('--required-players', type=int, help='Required players to start game (only for initial setup)')
    parser.add_argument('--server-id', default='server1', help='Server instance ID for logging')
    return parser.parse_args()

httpserver = None

# Tambahkan endpoint reset di HttpServer
if not hasattr(HttpServer, "reset_game"):
    def reset_game(self):
        if hasattr(self.game_state, 'reset_game_internal'):  # Redis mode
            self.game_state.reset_game_internal()
        else:  # Fallback mode
            self.reset_game_internal_fallback()
        logging.info("🔁 Game state has been reset by client request.")
    setattr(HttpServer, "reset_game", reset_game)

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        super().__init__(daemon=True)
        self.connection, self.address = connection, address
        # Track this connection
        ProcessTheClient.active_connections = getattr(ProcessTheClient, 'active_connections', 0) + 1

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
            # Decrease connection count
            ProcessTheClient.active_connections = getattr(ProcessTheClient, 'active_connections', 1) - 1
            logging.info(f"Connection with {self.address} closed (active: {ProcessTheClient.active_connections})")

class Server(threading.Thread):
    def __init__(self, port, args):
        super().__init__(daemon=False)
        self.the_clients, self.my_socket = [], socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True
        self.port = port
        self.args = args

    def run(self):
        global httpserver
        try:
            print("🔗 Testing Redis connection...")
            
            # Test Redis connection but don't exit on failure
            redis_available = False
            try:
                import redis
                test_redis = redis.Redis(host=self.args.redis_host, port=self.args.redis_port, decode_responses=True)
                test_redis.ping()
                
                # Test basic operations
                test_redis.set("test_key", "test_value")
                result = test_redis.get("test_key")
                test_redis.delete("test_key")
                
                print(f"✅ Redis connection test successful: {result}")
                redis_available = True
                
            except Exception as redis_error:
                print(f"⚠️ Redis connection failed: {redis_error}")
                print("🔄 Falling back to in-memory mode...")
                redis_available = False
            
            # Initialize HTTP server with or without Redis
            if redis_available:
                httpserver = HttpServer(
                    redis_host=self.args.redis_host,
                    redis_port=self.args.redis_port,
                    required_players=self.args.required_players
                )
                print(f"🔗 Running with Redis backend")
            else:
                # Force fallback mode by passing invalid Redis connection
                httpserver = HttpServer(
                    redis_host='invalid_host',  # This will trigger fallback
                    redis_port=9999,            # Invalid port
                    required_players=self.args.required_players or 2
                )
                print(f"💾 Running with in-memory backend")
            
            self.my_socket.bind(('0.0.0.0', self.port))
            self.my_socket.listen(5)
            self.my_socket.settimeout(1.0)
            
            required_players = httpserver.REQUIRED_PLAYERS
            
            logging.info(f"🚀 {self.args.server_id} started on 0.0.0.0:{self.port}")
            
            if redis_available:
                logging.info(f"🔗 Redis: {self.args.redis_host}:{self.args.redis_port}")
                logging.info(f"🎯 Required players: {required_players} (from Redis)")
            else:
                logging.info(f"💾 Mode: In-memory fallback")
                logging.info(f"🎯 Required players: {required_players} (from config)")
            
            # Test game state access
            try:
                test_status = httpserver.get_game_status('test')
                print(f"🧪 Game state test: {test_status.get('status', 'unknown')}")
                if test_status.get('status') == 'error':
                    print(f"⚠️ Game state test error: {test_status.get('message', 'Unknown error')}")
            except Exception as e:
                print(f"⚠️ Game state test failed: {e}")
            
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
            logging.error(f"❌ Server error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

    def stop(self):
        logging.info("Stopping server...")
        self.running = False
        for t in self.the_clients: 
            try:
                t.join(timeout=1.0)
            except:
                pass
        self.cleanup()

    def cleanup(self):
        try:
            if hasattr(self, 'my_socket'):
                self.my_socket.close()
            logging.info("Server socket closed")
        except Exception:
            pass

def signal_handler(sig, frame):
    print("\n🛑 Received interrupt signal (Ctrl+C)")
    print("Shutting down server gracefully...")
    global server
    if server:
        server.stop()
        server.join(timeout=3.0)
    
    # Cleanup Redis connection
    global httpserver
    if httpserver and hasattr(httpserver.game_state, 'cleanup'):
        httpserver.game_state.cleanup()
    
    print("✅ Server stopped. Goodbye!")
    sys.exit(0)

def main():
    args = parse_arguments()
    global server
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🎮 Starting Stroop Color Game Server...")
    print(f"🚀 Server ID: {args.server_id}")
    print(f"🔗 Redis: {args.redis_host}:{args.redis_port}")
    if args.required_players:
        print(f"🎯 Setting required players: {args.required_players}")
    else:
        print("🎯 Using existing Redis config for required players")
    print("🛑 Press Ctrl+C to stop the server")
    
    try:
        server = Server(args.port, args)
        server.start()
        while server.is_alive():
            server.join(timeout=1.0)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logging.error(f"Main thread error: {e}")
        if server: 
            server.stop()
    finally:
        print("Main thread exiting...")

if __name__ == "__main__":
    main()
