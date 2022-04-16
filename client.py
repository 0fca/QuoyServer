from multiprocessing import Condition, Event
import socket
import time
import threading

target_host = "192.168.1.203"
target_port = 27700
msgs = [
    "HELLO-FROM %s",
    "SEND oliwier"
]
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((target_host, target_port))
lock = Condition()
logged_in = False
event = threading.Event()

def hello(username : str):
    client.send(bytes(msgs[0] % username, 'UTF-8'))

def send_message_to(msg : str, to : str):
    client.sendall(bytes("SEND %s %s" % (to, msg), "UTF-8"))
    
def recv(client : socket.socket, event : Event):
    while not event.is_set():
        lock.acquire()
        global logged_in
        response = client.recv(4096)
        if response:
            decoded_response = response.decode("UTF-8")
            if decoded_response.startswith("HELLO"):
                print("Logged in as %s" % decoded_response.split(" ")[1])
                logged_in = True
            if decoded_response == "IN-USE":
                print("This name is already taken")
            if decoded_response.startswith("DELIVERY"):
                chunks = response.decode("UTF-8").split(" ")
                body = ''
                for i in range(2, len(chunks)):
                    body += ' ' + chunks[i]
                print(body.lstrip())
            lock.notify_all()
            lock.release()


def run():
    global logged_in
    while not logged_in:
        i = str(input("Your name: "))
        hello(i)
        time.sleep(1)
    cmd = ""
    user = ""
    print("At any time, !quit to quit")
    user = str(input("User name:"))

    while cmd != "!quit":
        cmd = str(input(">"))
        if cmd and cmd != "!quit":
            send_message_to(cmd, user)
            cmd = ''
        else:
            #client.close()
            event.set()
            exit(0)

if __name__ == '__main__':
    client_handler = threading.Thread(target = recv, args=(client,event,))
    client_handler.start()
    run()
    