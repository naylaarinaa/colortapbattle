import socket
import threading
import json

COLOR_LIST = [
    "RED", "GREEN", "BLUE", "YELLOW", "PURPLE", "BLACK",
    "GRAY", "ORANGE", "PINK", "BROWN"
]

class GameServer:
    def __init__(self, host='127.0.0.1', port=55555):
        self.server_address = (host, port)
        self.players = {}
        self.lock = threading.Lock()

    def handle_client(self, client_socket, address):
        print(f"Connection from {address} has been established.")
        player_id = str(len(self.players) + 1)
        with self.lock:
            self.players[player_id] = client_socket

        try:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                command = data.decode().strip()
                response = self.process_command(command, player_id)
                client_socket.sendall((json.dumps(response) + "\r\n\r\n").encode())
        finally:
            client_socket.close()
            with self.lock:
                if player_id in self.players:
                    del self.players[player_id]
            print(f"Connection from {address} closed.")

    def process_command(self, command, player_id):
        if command.startswith("get_all_players"):
            return {"status": "OK", "players": list(self.players.keys())}
        elif command.startswith("get_players_face"):
            return {"status": "OK", "face": "base64_encoded_image"}
        elif command.startswith("set_location"):
            return {"status": "OK"}
        elif command.startswith("get_location"):
            return {"status": "OK", "location": "100,200"}
        return {"status": "ERROR"}

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(self.server_address)
        server_socket.listen(5)
        print(f"Server listening on {self.server_address}")

        try:
            while True:
                client_socket, address = server_socket.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.start()
        finally:
            server_socket.close()

if __name__ == "__main__":
    game_server = GameServer()
    game_server.start()