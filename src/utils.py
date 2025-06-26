def serialize_data(data):
    import json
    return json.dumps(data).encode('utf-8')

def deserialize_data(data):
    import json
    return json.loads(data.decode('utf-8'))

def send_data(sock, data):
    serialized_data = serialize_data(data)
    sock.sendall(serialized_data)

def receive_data(sock):
    buffer = bytearray()
    while True:
        part = sock.recv(4096)
        if not part:
            break
        buffer.extend(part)
        if b'\r\n\r\n' in buffer:
            break
    return deserialize_data(buffer)