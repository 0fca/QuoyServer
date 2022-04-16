import socket
import time
import threading

target_host = "127.0.0.1"
target_port = 27700
msgs = [
    "HELLO-FROM %s",
    "SEND oliwier"
]
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((target_host, target_port))

def hello(username : str):
    client.send(bytes(msgs[0] % username, 'UTF-8'))
    response = client.recv(1024)
    return response.decode('UTF-8')

def run():
    i = str(input("Input: "))
    print(hello(i))
    #client.close()

if __name__ == '__main__':
    run()
    