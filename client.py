import socket
target_host = "127.0.0.1"
target_port = 27700
# create a socket connection
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# let the client connect
client.connect((target_host, target_port))
# send some data
client.send(bytes("SYN", 'UTF-8'))
# get some data
response = client.recv(4096)
print(response.decode('UTF-8'))