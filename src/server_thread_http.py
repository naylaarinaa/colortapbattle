from socket import *
import socket
import threading
import time
import sys
import logging
from http import HttpServer

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
		threading.Thread.__init__(self)

	def run(self):
		rcv = ""
		while True:
			try:
				data = self.connection.recv(4096)
				if data:
					d = data.decode()
					rcv = rcv + d
					if "\r\n\r\n" in rcv:
						logging.warning("data dari client: {}" . format(rcv))
						hasil = httpserver.proses(rcv)
						hasil = hasil + "\r\n\r\n".encode()
						logging.warning("balas ke  client: {}" . format(hasil))
						self.connection.sendall(hasil)
						rcv = ""
						self.connection.close()
						break
				else:
					break
			except OSError as e:
				break
		self.connection.close()



class Server(threading.Thread):
	def __init__(self):
		self.the_clients = []
		self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		threading.Thread.__init__(self)

	def run(self):
		self.my_socket.bind(('0.0.0.0', 8889))
		self.my_socket.listen(5)
		while True:
			self.connection, self.client_address = self.my_socket.accept()
			logging.warning("connection from {}".format(self.client_address))

			clt = ProcessTheClient(self.connection, self.client_address)
			clt.start()
			self.the_clients.append(clt)



def main():
	svr = Server()
	svr.start()

if __name__=="__main__":
	main()