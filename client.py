from datetime import datetime
from multiprocessing import Condition, Event
import socket
import time
import threading
import curses
from curses import textpad
import serial
import ssl

target_host = "127.0.0.1"
target_port = 27700
port = 'COM4'
encoding = 'ASCII'
msgs = [
    "REG %s",
    "SEND %s %s"
]
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ssl_sock = ssl.wrap_socket(client,
                           ca_certs="base.cer",
                           cert_reqs=ssl.CERT_REQUIRED,
                           ssl_version=ssl.PROTOCOL_TLSv1_2)
ssl_sock.connect((target_host, 27700))
lock = Condition()
logged_in = False
event = threading.Event()

def hello(username : str):
    ssl_sock.send(bytes(msgs[0] % username, encoding))

def send_message_to(msg : str, to : str):
    ssl_sock.send(bytes("SEND %s %s" % (to, msg), encoding))

def write_to_serial_port(ser : serial.Serial, msg : str):
    if ser:
        ser.write(bytes('T'+str(datetime.now().timestamp()), encoding))
        time.sleep(3)
        ser.write(bytes(msg, encoding))
        time.sleep(3)

def recv(client : socket.socket, event : Event, ser : serial.Serial):
    while not event.is_set():
        lock.acquire()
        global logged_in
        response = client.recv(4096)
        if response:
            decoded_response = response.decode(encoding)
            if decoded_response.startswith("REG-ACK"):
                #print("Registered as %s" % decoded_response.split(" ")[1])
                logged_in = True
            if decoded_response == "IN-USE":
                # FIXME: Remember to implement it using curses
                pass
            if decoded_response.startswith("DELIVERY"):
                chunks = response.decode(encoding).split(" ")
                body = ''
                for i in range(1, len(chunks)):
                    body += ' ' + chunks[i]
                cmd = body.lstrip().rstrip()+'\n'
                print(bytes(cmd, encoding))
                write_to_serial_port(ser, cmd)
            lock.notify_all()
            lock.release()

def read_serial(ser : serial.Serial):
    while ser and ser.isOpen():
        if ser.in_waiting > 0:
            print(ser.read_all().decode(encoding))
        time.sleep(0.2)
        
def run(stdscr, editwin):
    box = textpad.Textbox(editwin)
    user = ""
    global logged_in
    while not logged_in:
        box.edit()
        user = box.gather().strip()
        hello(user)
        time.sleep(1)
    stdscr.addstr(0, 0, "Enter quoy server command: (hit Ctrl-G to send)")
    stdscr.refresh()
    editwin = curses.newwin(5,30, 2,1)
    textpad.rectangle(stdscr, 0,0, 7, 32)
    stdscr.refresh()
    box = textpad.Textbox(editwin)
    box.edit()
    cmd = ''
    while cmd != "!quit":
        cmd = box.gather()
        if cmd and cmd != "!quit":
            send_message_to(cmd.strip(), user.strip())
            cmd = ''
        else:
            event.set()
            curses.nocbreak()
            stdscr.keypad(False)
            curses.echo()
            curses.endwin()
            exit(0)

if __name__ == '__main__':
    stdscr = curses.initscr()
    stdscr.clear()
    curses.noecho()
    stdscr.keypad(True)
    stdscr.addstr(0, 0, "Register as: (hit Ctrl-G to send)")
    editwin = curses.newwin(5,30, 2,1)
    textpad.rectangle(stdscr, 1,0, 7, 32)
    stdscr.refresh()

    try:
        ser = serial.Serial()
        ser.baudrate = 9600
        ser.port = port
        ser.open()
    except Exception as e:
        pass
    client_handler = threading.Thread(target = recv, args=(ssl_sock,event,ser,), daemon=False)
    client_handler.start()
    client_handler = threading.Thread(target = read_serial, args=(ser,), daemon=False)
    client_handler.start()
    run(stdscr, editwin)