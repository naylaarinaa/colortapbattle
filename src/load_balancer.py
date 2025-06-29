import socket
import threading
import time
import json
import logging
import signal
import sys
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

class LoadBalancer:
    def __init__(self, listen_port=8888, backend_servers=None):
        self.listen_port = listen_port
        self.backend_servers = backend_servers or [
            {'host': '127.0.0.1', 'port': 8889},
            {'host': '127.0.0.1', 'port': 8890},
            {'host': '127.0.0.1', 'port': 8891}
        ]
        
        # Round robin state
        self.current_server_index = 0
        self.server_lock = threading.Lock()
        
        # Health check
        self.healthy_servers = []
        self.last_health_check = 0
        
        # Shutdown control
        self.running = True
        self.server_socket = None
        
        logger.info(f"🔄 Load Balancer initialized on port {listen_port}")
        logger.info(f"📋 Backend servers: {self.backend_servers}")

    def check_server_health(self, server, timeout=2):
        """Check if backend server is healthy"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((server['host'], server['port']))
                return True
        except Exception:
            return False

    def update_healthy_servers(self):
        """Update list of healthy servers"""
        current_time = time.time()
        
        # Check health every 5 seconds
        if current_time - self.last_health_check < 5:
            return
        
        self.last_health_check = current_time
        healthy = []
        
        for server in self.backend_servers:
            if self.check_server_health(server):
                healthy.append(server)
                logger.debug(f"✅ Server {server['host']}:{server['port']} healthy")
            else:
                logger.warning(f"❌ Server {server['host']}:{server['port']} unhealthy")
        
        if healthy != self.healthy_servers:
            server_list = [f"{s['host']}:{s['port']}" for s in healthy]
            logger.info(f"🔄 Healthy servers updated: {server_list}")
            self.healthy_servers = healthy

    def get_next_server_round_robin(self):
        """Get next server using round robin"""
        with self.server_lock:
            if not self.healthy_servers:
                return None
            
            server = self.healthy_servers[self.current_server_index % len(self.healthy_servers)]
            self.current_server_index = (self.current_server_index + 1) % len(self.healthy_servers)
            
            logger.info(f"🎯 Round Robin: Client → {server['host']}:{server['port']} (index: {self.current_server_index-1})")
            return server

    def proxy_request(self, client_socket, client_address):
        """Proxy request to backend server"""
        backend_socket = None
        try:
            # Check if we should continue
            if not self.running:
                return
                
            # Update server health
            self.update_healthy_servers()
            
            # Get target server
            target_server = self.get_next_server_round_robin()
            if not target_server:
                logger.error("🚫 No healthy backend servers available")
                try:
                    client_socket.send(b"HTTP/1.1 503 Service Unavailable\r\n\r\nNo servers available")
                except:
                    pass
                return
            
            logger.info(f"🔄 Proxying {client_address} → {target_server['host']}:{target_server['port']}")
            
            # Connect to backend server
            backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_socket.settimeout(5)  # Shorter timeout
            backend_socket.connect((target_server['host'], target_server['port']))
            
            # Set non-blocking mode for graceful shutdown
            client_socket.settimeout(1.0)
            backend_socket.settimeout(1.0)
            
            # Simple data forwarding loop instead of threads
            while self.running:
                try:
                    # Forward client data to server
                    try:
                        data = client_socket.recv(4096)
                        if not data:
                            break
                        backend_socket.send(data)
                    except socket.timeout:
                        pass
                    except Exception:
                        break
                    
                    # Forward server data to client
                    try:
                        data = backend_socket.recv(4096)
                        if not data:
                            break
                        client_socket.send(data)
                    except socket.timeout:
                        pass
                    except Exception:
                        break
                        
                except Exception as e:
                    logger.debug(f"🔄 Proxy loop error: {e}")
                    break
            
        except Exception as e:
            logger.error(f"❌ Proxy error for {client_address}: {e}")
        finally:
            # Clean up connections
            try:
                if client_socket:
                    client_socket.close()
            except:
                pass
            try:
                if backend_socket:
                    backend_socket.close()
            except:
                pass

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Initiating graceful shutdown...")
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        logger.info("✅ Load Balancer stopped")

    def start(self):
        """Start load balancer"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind(('0.0.0.0', self.listen_port))
            self.server_socket.listen(10)
            self.server_socket.settimeout(1.0)  # Non-blocking accept
            
            logger.info(f"🚀 Load Balancer started on 0.0.0.0:{self.listen_port}")
            server_list = [f"{s['host']}:{s['port']}" for s in self.backend_servers]
            logger.info(f"🎯 Round Robin to: {server_list}")
            logger.info("💡 Press Ctrl+C to stop")
            
            # Initial health check
            self.update_healthy_servers()
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    
                    # Handle each client in separate thread
                    handler = threading.Thread(
                        target=self.proxy_request,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    handler.start()
                    
                except socket.timeout:
                    # Normal timeout, continue loop
                    continue
                except KeyboardInterrupt:
                    logger.info("🛑 Ctrl+C received")
                    break
                except Exception as e:
                    if self.running:  # Only log if we're still supposed to be running
                        logger.error(f"❌ Accept error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"❌ Load Balancer failed to start: {e}")
        finally:
            self.shutdown()

def signal_handler(signum, frame):
    """Handle Ctrl+C signal"""
    logger.info("🛑 Signal received, shutting down...")
    if 'lb' in globals():
        lb.shutdown()
    sys.exit(0)

def main():
    import argparse
    
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description='Color Tap Battle Load Balancer')
    parser.add_argument('--port', type=int, default=8888, help='Load balancer listen port (default: 8888)')
    parser.add_argument('--backends', default='8889,8890,8891', help='Backend server ports (default: 8889,8890,8891)')
    parser.add_argument('--host', default='127.0.0.1', help='Backend server host (default: 127.0.0.1)')
    
    args = parser.parse_args()
    
    # Parse backend servers
    backend_ports = [int(p.strip()) for p in args.backends.split(',')]
    backend_servers = [{'host': args.host, 'port': port} for port in backend_ports]
    
    # Create and start load balancer
    global lb
    lb = LoadBalancer(listen_port=args.port, backend_servers=backend_servers)
    
    try:
        lb.start()
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        logger.info("🔚 Load Balancer exited")

if __name__ == "__main__":
    main()