from concurrent.futures import thread
from http import server
from multiprocessing import Event
import socket
import threading
import time
from logger import Logger
import ssl
from session_manager import Session
from session_manager import SessionManager
from session_manager import Response

class Command():
    def __init__(self, func : callable, body_start_index : int):
        self.func = func
        self.__body_start_index = body_start_index

    def body_start_index(self):
        return self.__body_start_index
    
    def exec(self, args : list = [], session_manager : SessionManager = None, opt_args = []) -> Response:
        return self.func(args, session_manager, opt_args)


class FunctionSet():
    @staticmethod
    def on_hello(args : list, session_manager : SessionManager, opt_args = []) -> Response:
        r = Response("REG-ACK " + args[0])
        session = session_manager.existing_session_by_username(args[0])
        if session:
            r = Response("IN-USE")
            return r
        session : Session = session_manager.existing_session_by_ip(opt_args[0])
        if session:
            session.assign_user(args[0])
            return r
        else:
            return None

    @staticmethod
    def on_send_ok(args : list,  session_manager : SessionManager, opt_args = []) -> Response:
        session = session_manager.existing_session_by_username(args[0])
        if session:
            r = Response("SEND-OK")
            r2 = Response("DELIVERY %s" % (args[1]))
            session.write_response_for(r2, args[0])
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
        self.event_locks = {}
        self.logger = logger
        self.__session_manager = None
        self.command_set = {
            "REG" : Command(FunctionSet.on_hello, -1),
            "SEND" : Command(FunctionSet.on_send_ok, 2),
            "UNREG" : Command(FunctionSet.on_unreg, -1)
        }
        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server.bind((self.__bind_ip, self.__bind_port))
        self.__server.listen(5)
        self.logger.info("Listening on %s:%d" % (self.__bind_ip, self.__bind_port))

    def __handle_client(self, client_socket, event : Event, logger : Logger, session_manager : SessionManager):
        sip = client_socket.getpeername()[0]
        while not event.is_set():
            try:
                request = client_socket.recv(4096)
                if not request:
                    continue
                logger.info("Received: %s on %s" % (request, threading.current_thread().name))
                if type(client_socket) is socket.socket and request[0] == 255:
                    self.logger.info("Received ff byte from %s, skipping over..." % sip)
                    client_socket.close()
                    break
                command = CommandParser.find_command(request.decode("ascii"), self.command_set)
                parsed_command = CommandParser.parse_command(request.decode("ascii"), command.body_start_index())
                args = []
                for arg_index in range(1, len(parsed_command)):
                    args.append(parsed_command[arg_index])
                response = command.exec(args, session_manager, [client_socket.getpeername()[0]])
                if response:
                    logger.info("Sending back %s on %s" % (response.to_str(), threading.current_thread().name))
                    client_socket.sendall(bytes(response.to_str()))
            except Exception as e:
                logger.err(str(e))
                client_socket.close()
                break
            time.sleep(0.5)
        self.logger.info("Halting session %s ..." % sip)
        session_manager.halt_session(sip)

    def __handle_buffer_out(self, logger : Logger, session_manager : SessionManager):
        while True:
            session_manager.handle_buffer_out()
            time.sleep(1)

    def launch(self):
        self.__session_manager = SessionManager()
        client_handler = threading.Thread(target = self.__handle_buffer_out, args=(self.logger,self.__session_manager,), name="Buffer_Writer")
        client_handler.start()
        while True:
            self.logger.info("There are alredy %d thread active" % threading.active_count())
            client, addr = self.__server.accept()
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(certfile="base.cer", keyfile="cert.key")
            connstream = context.wrap_socket(client, server_side=True)
            s = self.__session_manager.create(connstream)
            self.logger.info("Accepted connection from: %s:%d" % (addr[0], addr[1]))
            client_handler = threading.Thread(target = self.__handle_client, args=(connstream, s.lock_event(), self.logger, self.__session_manager), name="SocketHandler%s" % (addr[0]))
            client_handler.start()


if __name__ == '__main__':
    server = Server('0.0.0.0')
    server.launch()
    