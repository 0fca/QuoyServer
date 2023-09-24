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

'''
This class represents a simple TCP server. It implements simple protocol over TCP - Quoy protocol.
For now, this class supports virtual host concept using multiserver architecture.
It is able to load simple modules (plain, Python script files), 
which can be used anywhere inside the code to cleanly implkement different features.
'''
class Server():
    def __init__(self, vhost : dict, logger : Logger):
        self.__bind_ip = vhost["HOST"]
        self.__bind_port = vhost["PORT"]
        self.event_locks = {}
        self.logger = logger
        self.__session_manager = None
        # TODO: The commands should be outside this file - it shall be done using "modules" mechanism of the server
        self.command_set = {
            "REG" : Command(FunctionSet.on_hello, -1),
            "SEND" : Command(FunctionSet.on_send_ok, 2),
            "UNREG" : Command(FunctionSet.on_unreg, 1),
            ".SYSSTA": Command(FunctionSet.on_systems_status, 2)
        }
        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server.bind((self.__bind_ip, self.__bind_port))
        self.__server.listen(5)
        self.logger.info("Listening on %s:%d and ready to accept connections..." % (self.__bind_ip, self.__bind_port))

    '''
    Handle client using raw AF_INET socket (TCP socket). 
    This handler is compatible with either Linux and Windows networking abstraction layer.
    Default length of packets is 4096 bytes.
    '''
    def __handle_client(self, client_socket : socket.socket, event : Event, session_manager : SessionManager):
        sip = client_socket.getpeername()[0]
        while not event.is_set():
            try:
                request = client_socket.recv(4096)
                if not request:
                    continue
                self.logger.debug("Received: %s on %s" % (request, threading.current_thread().name))
                if type(client_socket) is not ssl.SSLSocket and request[0] == 255:
                    self.logger.debug("Received ff byte from %s, skipping over..." % sip)
                    client_socket.close()
                    break
                if request == b'\r\n':
                    self.logger.debug("Received CR and NL bytes, probably raw Windows telnet client, skipping over...")
                    continue
                command = CommandParser.find_command(request.decode("ascii"), self.command_set)
                parsed_command = CommandParser.parse_command(request.decode("ascii"), command.body_start_index())
                args = []
                for arg_index in range(1, len(parsed_command)):
                    args.append(parsed_command[arg_index])
                response = command.exec(args, session_manager, [client_socket.getpeername()[0], MODULE_REFS])
                if response:
                    self.logger.debug("Sending back %s on %s" % (response.to_str(), threading.current_thread().name))
                    client_socket.sendall(bytes(response.to_str()))
            except Exception as e:
                self.logger.severe(str(e))
                client_socket.close()
                break
            time.sleep(0.5)
        self.logger.debug("Halting session %s ..." % sip)
        session_manager.halt_session(sip)

    '''
    This method is passed as a invokeable to isolated thread scope so writing and reading of TCP packets is isolated one from each other.
    '''
    def __handle_buffer_out(self, logger : Logger, session_manager : SessionManager):
        while True:
            session_manager.handle_buffer_out()
            time.sleep(1)

    '''
    This method allows to launch the Server class instance, it can be called only once per Server instance.
    It allows to launch server using vhost configs including TLS support.
    '''
    def launch(self, vconfig : dict):
        self.__session_manager = SessionManager()
        client_handler = threading.Thread(target = self.__handle_buffer_out, args=(self.logger,self.__session_manager,), name="Buffer_Writer")
        client_handler.start()
        while True:
            self.logger.info("Active Thread Count: %s" % threading.active_count())
            client, addr = self.__server.accept()
            # This if is a contextual check whether the module ssl is enabled, if so we should try creating SSL socket
            if "ssl" in modules_config["ENABLED"] and vconfig["TLS"]:
                # Read a reference to a module - all references are now loaded in an entrypoint
                m = MODULE_REFS["mod_ssl"]
                # Retrieve __mod_init__ reference so we can call it thus initialize a module
                mod_init_func = getattr(m, "__mod_init__")
                # Invoke __mod_init__ function to initalize module instance for current vhost
                client = mod_init_func({
                    "certfile": vconfig["CERT_FILE"],
                    "keyfile": vconfig["KEY_FILE"]
                })
            s = self.__session_manager.create(client)
            self.logger.debug("Accepted connection from: %s:%d" % (addr[0], addr[1]))
            client_handler = threading.Thread(target = self.__handle_client, args=(client, s.lock_event(), self.__session_manager), name="SocketHandler%s" % (addr[0]))
            client_handler.start()
            
# Just an entrypoint
if __name__ == '__main__':
    module_loader = ModuleLoader()
    module_loader.load_all(MODULE_REFS)
    for vhost in net_conf["VHOSTS"]:
        logger = Logger()
        server = Server(vhost, logger)
        server.launch(vhost)
    