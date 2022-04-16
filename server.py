from concurrent.futures import thread
from http import server
import socket
import threading
import uuid
import time

class Session():
    def __init__(self, ip : str):
        self.__sid = uuid.uuid4()
        self.__ip = ip
        self.__socket = None
        self.__username = ""
    
    def assign_user(self, username : str):
        self.__username = username

    def assing_socket(self, socket : socket.socket):
        self.__socket = socket

    def socket(self) -> socket.socket:
        return self.__socket

    def sid(self) -> str:
        return self.__sid
    
    def username(self) -> str:
        return self.__username
    
    def ip(self) -> str:
        return self.__ip

class Response():
    def __init__(self, payload : str):
        self.__payload = payload

    def to_str(self, enc : str = "UTF-8") -> bytes:
        return bytes(self.__payload, enc)

class Command():
    def __init__(self, func : callable, body_start_index : int):
        self.func = func
        self.__body_start_index = body_start_index

    def body_start_index(self):
        return self.__body_start_index
    
    def exec(self, args : list = [], session_queue : list = [], opt_args = []) -> tuple[Response, socket.socket, Response]:
        return self.func(args, session_queue, opt_args)

class FunctionSet():
    def create_session_if_needed(session_queue : list[Session], ip : str, socket : socket.socket):
        s = Session(ip)
        s.assing_socket(socket)
        filtered_sessions = list(filter(lambda s : (s.ip() == ip), session_queue))
        if not filtered_sessions:
            session_queue.append(s)

    @staticmethod
    def on_hello(args : list, session_queue : list[Session], opt_args = []) -> tuple[Response, socket.socket, Response]:
        r = Response("HELLO " + args[0])
        session : Session = list(filter(lambda s : (s.username() == args[0]), session_queue))
        if session:
            r = Response("IN-USE")
            return (r, None, None)
        sessions: list[Session] = list(filter(lambda s : (s.ip() == opt_args[0]), session_queue))
        if sessions:
            sessions[0].assign_user(args[0])
            return (r, sessions[0].socket(), None)
        else:
            return (None, None, None)

    @staticmethod
    def on_send_ok(args : list,  session_queue : list, opt_args = []) -> tuple[Response, socket.socket, Response]:
        sessions : list[Session] = list(filter(lambda s : (s.username() == args[0]), session_queue))
        print(args[0])
        if sessions:
            r = Response("SEND-OK")
            r2 = Response("DELIVERY %s %s" % (args[0], args[1]))
            return (r, sessions[0].socket(), r2)
        else:
            print("sessions empty")
            return (None, None, None)

class CommandParser():
    @staticmethod
    def parse_command(command_text : str, body_start_index : int = 2) -> list:
        chunks = command_text.rstrip().split(" ")
        parsed_command = []
        if body_start_index != -1:
            for i in range(0, body_start_index):
                parsed_command.append(chunks[i])
            body = ''
            for i in range(body_start_index, len(chunks)):
                body += ' ' + chunks[i]
            parsed_command.append(body.lstrip())
        else:
            parsed_command = chunks
        return parsed_command
    
    @staticmethod
    def find_command(command_text, command_set : list) -> Command:
        return command_set[command_text.rstrip().split(" ")[0]]
    
class Server():
    def __init__(self, ip : str = "127.0.0.1", port : int = 27700):
        self.__bind_ip = ip
        self.__bind_port = port
        self.session_queue = []
        self.command_set = {
            "HELLO-FROM" : Command(FunctionSet.on_hello, -1),
            "SEND" : Command(FunctionSet.on_send_ok, 2)
        }
        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server.bind((self.__bind_ip, self.__bind_port))
        self.__server.listen(5)
        print("[*] Listening on %s:%d" % (self.__bind_ip, self.__bind_port))

    def __handle_client(self, client_socket : socket.socket):
        while True:
            try:
                request = client_socket.recv(4096)
                if not request:
                    continue
                print("[*] Received: %s on %s" % (request, threading.current_thread().name))
                command = CommandParser.find_command(request.decode("UTF-8"), self.command_set)
                parsed_command = CommandParser.parse_command(request.decode("UTF-8"), command.body_start_index())
                args = []
                for arg_index in range(1, len(parsed_command)):
                    args.append(parsed_command[arg_index])
                response, client_socket2, return_response = command.exec(args, self.session_queue, [client_socket.getpeername()[0]])
                print("[*] Sending back %s on %s" % (response.to_str(), threading.current_thread().name))
                client_socket.sendall(bytes(response.to_str()))
                if client_socket2 and return_response:
                    print("[*] Sending %s on %s" % (return_response.to_str(), threading.current_thread().name))
                    client_socket2.send(bytes(return_response.to_str()))
            except Exception as e:
                print(threading.current_thread().name)
                print(e.args)
                if client_socket2 and type(client_socket2) is socket.socket:
                    session : Session = list(filter(lambda s : (s.ip() == client_socket2.getpeername()[0]), self.session_queue))[0]
                    self.session_queue.remove(session)
                    client_socket2.close()
                elif client_socket2:
                    del client_socket2
                client_socket.close()
                return
    def __socket_queue_cleaner(self):
        while True:
            for session in self.session_queue:
                if session:
                    s = session.socket()
                    if s:
                        try:
                            if type(s) is socket.socket:
                                s.sendall(bytes("PING", "UTF-8"))     
                            time.sleep(2)
                        except:
                            print("Cleaning... session of %s" % session.username())
                            del s
                            self.session_queue.remove(session)
                            del session

    def launch(self):
        while True:
            print("[*] There are alredy %d thread active" % threading.active_count())
            client, addr = self.__server.accept()
            FunctionSet.create_session_if_needed(self.session_queue, client.getpeername()[0], client)
            print("[*] Accepted connection from: %s:%d" % (addr[0], addr[1]))
            client_handler = threading.Thread(target = self.__handle_client, args=(client,))
            client_handler.start()
            client_handler = threading.Thread(target = self.__socket_queue_cleaner)
            client_handler.start()


if __name__ == '__main__':
    server = Server('0.0.0.0')
    server.launch()
    