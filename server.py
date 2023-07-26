from config import MODULES as modules_config
from config import NET_CONF as net_conf
from multiprocessing import Event
from module_loader import ModuleLoader
import socket
import threading
import time
from logger import Logger
import ssl
from session_manager import SessionManager
from commands.command_parser import CommandParser
from commands.command import Command
from commands.function_set import FunctionSet

MODULE_REFS = {}

class Server():
    def __init__(self, vhost : dict, logger : Logger):
        self.__bind_ip = vhost["HOST"]
        self.__bind_port = vhost["PORT"]
        self.event_locks = {}
        self.logger = logger
        self.__session_manager = None
        self.command_set = {
            "REG" : Command(FunctionSet.on_hello, -1),
            "SEND" : Command(FunctionSet.on_send_ok, 2),
            "UNREG" : Command(FunctionSet.on_unreg, 1)
        }
        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server.bind((self.__bind_ip, self.__bind_port))
        self.__server.listen(5)
        self.logger.info("Listening on %s:%d" % (self.__bind_ip, self.__bind_port))

    def __handle_client(self, client_socket : socket.socket, event : Event, session_manager : SessionManager):
        sip = client_socket.getpeername()[0]
        while not event.is_set():
            try:
                request = client_socket.recv(4096)
                if not request:
                    continue
                self.logger.info("Received: %s on %s" % (request, threading.current_thread().name))
                if type(client_socket) is not ssl.SSLSocket and request[0] == 255:
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
                    self.logger.info("Sending back %s on %s" % (response.to_str(), threading.current_thread().name))
                    client_socket.sendall(bytes(response.to_str()))
            except Exception as e:
                self.logger.err(str(e))
                client_socket.close()
                break
            time.sleep(0.5)
        self.logger.info("Halting session %s ..." % sip)
        session_manager.halt_session(sip)

    def __handle_buffer_out(self, logger : Logger, session_manager : SessionManager):
        while True:
            session_manager.handle_buffer_out()
            time.sleep(1)

    def launch(self, vconfig : dict):
        self.__session_manager = SessionManager()
        client_handler = threading.Thread(target = self.__handle_buffer_out, args=(self.logger,self.__session_manager,), name="Buffer_Writer")
        client_handler.start()
        while True:
            self.logger.info("Active Thread Count: %s" % threading.active_count())
            client, addr = self.__server.accept()
            if "ssl" in modules_config["ENABLED"] and vconfig["TLS"]:
                m = MODULE_REFS["mod_ssl"]
                mod_init_func = getattr(m, "__mod_init__")
                client = mod_init_func({
                    "certfile": vconfig["CERT_FILE"],
                    "keyfile": vconfig["KEY_FILE"]
                })
            s = self.__session_manager.create(client)
            self.logger.info("Accepted connection from: %s:%d" % (addr[0], addr[1]))
            client_handler = threading.Thread(target = self.__handle_client, args=(client, s.lock_event(), self.__session_manager), name="SocketHandler%s" % (addr[0]))
            client_handler.start()

if __name__ == '__main__':
    module_loader = ModuleLoader()
    module_loader.load_all(MODULE_REFS)
    for vhost in net_conf["VHOSTS"]:
        logger = Logger()
        server = Server(vhost, logger)
        server.launch(vhost)
    