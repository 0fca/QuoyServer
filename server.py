from concurrent.futures import thread
from http import server
from multiprocessing import Event
import socket
import threading
import uuid
import time
from logger import Logger

class Response():
    def __init__(self, payload : str):
        self.__payload = payload

    def to_str(self, enc : str = "ASCII") -> bytes:
        return bytes(self.__payload + "\r\n", enc)


class Session():
    def __init__(self, ip : str):
        self.__sid = uuid.uuid4()
        self.__ip = ip
        self.__socket = None
        self.__username = ""
        self.__buffer_out : dict[list] = {}
    
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
    
    def read_all_for_username(self, username : str) -> list[str]:
        if username in self.__buffer_out:
            return self.__buffer_out[username]
        else:
            return []
    
    def write_response_for(self, response : Response, username : str):
        if username in self.__buffer_out:
            self.__buffer_out[username].append(response)
        else:
            self.__buffer_out[username] = [response]

    def wipe_buffer(self):
        self.__buffer_out.clear()


class Command():
    def __init__(self, func : callable, body_start_index : int):
        self.func = func
        self.__body_start_index = body_start_index

    def body_start_index(self):
        return self.__body_start_index
    
    def exec(self, args : list = [], session_queue : list = [], opt_args = []) -> Response:
        return self.func(args, session_queue, opt_args)


class FunctionSet():
    def create_session_if_needed(session_queue : list[Session], ip : str, socket : socket.socket):
        s = Session(ip)
        s.assing_socket(socket)
        filtered_sessions = list(filter(lambda s : (s.ip() == ip), session_queue))
        if not filtered_sessions:
            session_queue.append(s)

    @staticmethod
    def on_hello(args : list, session_queue : list[Session], opt_args = []) -> Response:
        r = Response("REG-ACK " + args[0])
        session : Session = list(filter(lambda s : (s.username() == args[0]), session_queue))
        if session:
            r = Response("IN-USE")
            return r
        sessions: list[Session] = list(filter(lambda s : (s.ip() == opt_args[0]), session_queue))
        if sessions:
            sessions[0].assign_user(args[0])
            return r
        else:
            return None

    @staticmethod
    def on_send_ok(args : list,  session_queue : list, opt_args = []) -> Response:
        sessions : list[Session] = list(filter(lambda s : (s.username() == args[0]), session_queue))
        if sessions:
            r = Response("SEND-OK")
            r2 = Response("DELIVERY %s" % (args[1]))
            sessions[0].write_response_for(r2, args[0])
            return r
        else:
            return Response("BAD-RQST-BDY No session found for %s" % args[0])

    @staticmethod
    def on_bad_rqst_hdr(args : list,  session_queue : list, opt_args = []):
        return Response("BAD-RQST-HDR")

    @staticmethod
    def on_unreg(args : list, session_queue : list, opt_args = []):
        return Response("NOT-IMPL")


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
        command_str = command_text.rstrip().split(" ")[0]
        if command_str in command_set:
            return command_set[command_str]
        else:
            return Command(FunctionSet.on_bad_rqst_hdr, -1)
    

class Server():
    def __init__(self, ip : str = "127.0.0.1", logger : Logger = Logger(), port : int = 27700):
        self.__bind_ip = ip
        self.__bind_port = port
        self.session_queue = []
        self.event_locks = {}
        self.logger = logger
        self.command_set = {
            "REG" : Command(FunctionSet.on_hello, -1),
            "SEND" : Command(FunctionSet.on_send_ok, 2),
            "UNREG" : Command(FunctionSet.on_unreg, -1)
        }
        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server.bind((self.__bind_ip, self.__bind_port))
        self.__server.listen(5)
        self.logger.info("Listening on %s:%d" % (self.__bind_ip, self.__bind_port))

    def __handle_client(self, client_socket : socket.socket, event : Event, logger : Logger):
        sip = client_socket.getpeername()[0]
        while not event.is_set():
            try:
                request = client_socket.recv(4096)
                if not request:
                    continue
                logger.info("Received: %s on %s" % (request, threading.current_thread().name))
                if request[0] == 255:
                    self.logger.info("Received ff byte from %s, skipping over..." % sip)
                    client_socket.close()
                    break
                command = CommandParser.find_command(request.decode("ascii"), self.command_set)
                parsed_command = CommandParser.parse_command(request.decode("ascii"), command.body_start_index())
                args = []
                for arg_index in range(1, len(parsed_command)):
                    args.append(parsed_command[arg_index])
                response = command.exec(args, self.session_queue, [client_socket.getpeername()[0]])
                if response:
                    logger.info("Sending back %s on %s" % (response.to_str(), threading.current_thread().name))
                    client_socket.sendall(bytes(response.to_str()))
            except Exception as e:
                logger.err(str(e))
                client_socket.close()
                break
            time.sleep(0.5)
        sessions : list[Session] = list(filter(lambda s : (s.ip() == sip), self.session_queue))
        if sessions and sessions[0] in self.session_queue:
            self.session_queue.remove(sessions[0])
            del sessions[0]

    def __handle_buffer_out(self, logger : Logger):
        while True:
            for session in self.session_queue:
                socket : socket.socket = session.socket()
                if session and session.username():
                    for msg in session.read_all_for_username(session.username()):
                        try:
                            logger.info("Writing %s to socket of %s" % (msg.to_str(), session.username()))
                            socket.sendall(bytes(msg.to_str()))
                        except OSError as e:
                            self.logger.err(e)
                            if session in self.session_queue:
                               self.session_queue.remove(session)
                            socket.close()
                            if session.ip() in self.event_locks:
                                self.event_locks[session.ip()].set()
                                del self.event_locks[session.ip()]
                        except Exception as e:
                            logger.err(str(e))
                            self.event_locks[session.ip()].set()

                    if session:
                        session.wipe_buffer()
            time.sleep(1)
    def launch(self):
        client_handler = threading.Thread(target = self.__handle_buffer_out, args=(self.logger,), name="Buffer_Writer")
        client_handler.start()
        while True:
            self.logger.info("There are alredy %d thread active" % threading.active_count())
            client, addr = self.__server.accept()
            FunctionSet.create_session_if_needed(self.session_queue, client.getpeername()[0], client)
            self.logger.info("Accepted connection from: %s:%d" % (addr[0], addr[1]))
            event = Event()
            self.event_locks[addr[0]] = event
            client_handler = threading.Thread(target = self.__handle_client, args=(client,event,self.logger), name="SocketHandler%s" % (addr[0]))
            client_handler.start()


if __name__ == '__main__':
    server = Server('0.0.0.0')
    server.launch()
    