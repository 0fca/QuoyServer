from http import server
from re import S
import socket
import threading
import uuid

class Session():
    def __init__(self, ip : str):
        self.__sid = uuid.uuid4()
        self.__ip = ip
        self.__socket = None
    
    def assing_user(self, username : str):
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
    def __init__(self, msg : str, func : callable):
        self.msg = msg
        self.func = func

    def as_text(self) -> str:
        return self.msg

    def exec(self, args : list = [], session_queue : list = [], opt_args = []) -> tuple[Response, socket.socket]:
        return self.func(self, args, session_queue, opt_args)

class FunctionSet():
    def create_session_if_needed(session_queue : list[Session], ip : str, socket : socket.socket):
        s = Session(ip)
        s.assing_socket(socket)
        filtered_sessions = list(filter(lambda s : (s.ip() == ip), session_queue))
        if not filtered_sessions:
            session_queue.append(s)

    @staticmethod
    def on_hello(command : Command, args : list, session_queue : list[Session], opt_args = []) -> tuple[Response, socket.socket]:
        r = Response(command.as_text() + " " + args[0])
        session : Session = list(filter(lambda s : (s.ip() == opt_args[0]), session_queue))[0]
        session.assing_user(args[0])
        return (r, session.socket())

    @staticmethod
    def on_send_ok(command : Command, args : list,  session_queue : list, opt_args = []) -> tuple[Response, socket.socket]:
        session : Session = list(filter(lambda s : (s.ip() == opt_args[0]), session_queue))[0]
        return (Response(command.as_text()), session.socket())

class CommandParser():
    @staticmethod
    def parse_command(command_text : str) -> list:
        return command_text.rstrip().split(" ")

class Server():
    def __init__(self, ip : str = "127.0.0.1", port : int = 27700):
        self.__bind_ip = ip
        self.__bind_port = port
        self.session_queue = []
        self.command_set = {
            "HELLO-FROM" : Command("HELLO", FunctionSet.on_hello),
            "SEND" : Command("SEND-OK", FunctionSet.on_send_ok)
        }
        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server.bind((self.__bind_ip, self.__bind_port))
        self.__server.listen(5)
        print("[*] Listening on %s:%d" % (self.__bind_ip, self.__bind_port))

    def __handle_client(self, client_socket : socket.socket):
        while True:
            request = client_socket.recv(1024)
            if not request:
                continue
            print("[*] Received: %s" % request)
            parsed_command = CommandParser.parse_command(request.decode("UTF-8"))
            command = self.command_set[parsed_command[0]]
            args = []
            for arg_index in range(1, len(parsed_command)):
                args.append(parsed_command[arg_index])
            response, socket = command.exec(args, self.session_queue, [client_socket.getpeername()[0]])
            print(response)
            print(socket)
            socket.send(bytes(response.to_str()))

    def launch(self):
        while True:
            client, addr = self.__server.accept()
            FunctionSet.create_session_if_needed(self.session_queue, client.getpeername()[0], client)

            print("[*] Accepted connection from: %s:%d" % (addr[0], addr[1]))
            client_handler = threading.Thread(target = self.__handle_client, args=(client,))
            client_handler.start()


if __name__ == '__main__':
    server = Server()
    server.launch()
    