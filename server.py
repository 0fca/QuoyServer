import socket
import threading
bind_ip = "0.0.0.0"
bind_port = 27700
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((bind_ip, bind_port))
server.listen(5)
print("[*] Listening on %s:%d" % (bind_ip, bind_port))
# This is the thread we handle the data from  the client
def handle_client(client_socket):
    # show the data from the client
    request = client_socket.recv(1024)
    print("[*] Received: %s" % request)
    # Return a packet
    client_socket.send(bytes("ACK with PL: ąćężź!", "UTF-8"))
    client_socket.close()
while True:
    client, addr = server.accept()
    print("[*] Accepted connection from: %s:%d" % (addr[0], addr[1]))
    # activate the function to handle the data from client
    client_handler = threading.Thread(target = handle_client, args=(client,))
    client_handler.start()