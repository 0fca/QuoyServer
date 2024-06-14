from config import MODULES as modules_config
from config import NET_CONF as net_conf
from config import RUNTIME as runtime_conf
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
from console.console_server import launch_server
import datetime
import os

'''
The dictionary represents a dependency container of plug-in server modules
'''
MODULE_REFS = {}

'''
This class represents a simple TCP server. It implements simple protocol over TCP - Quoy protocol.
For now, this class supports virtual host concept using multiserver architecture.
It is able to load simple modules (plain, Python script files), 
which can be used anywhere inside the code to cleanly implkement different features.
'''
class Server():
    def __init__(self, vhost : dict, logger : Logger):
        self.is_crash_recovery_set : bool = False
        self.__bind_ip = vhost["HOST"]
        self.__bind_port = vhost["PORT"]
        self.logger = logger
        self.__session_manager = None
        self.keep_running = Event()
        # TODO: The commands should be outside this file - it shall be done using "modules" mechanism of the server
        self.command_set = {
            "REG" : Command(FunctionSet.on_hello, -1),
            "SEND" : Command(FunctionSet.on_send_ok, 2),
            "UNREG" : Command(FunctionSet.on_unreg, 1),
            ".SYSSTA": Command(FunctionSet.on_systems_status, 2),
            ".USRNFO": Command(FunctionSet.on_user_info, 2)
        }
        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__server.setblocking(False)
        self.__server.bind((self.__bind_ip, self.__bind_port))
        self.__server.listen(0)
        self.logger.info("Listening on %s:%d and ready to accept connections..." % (self.__bind_ip, self.__bind_port))

    '''
    Handle client using raw AF_INET socket (TCP socket). 
    This handler is compatible with either Linux and Windows networking abstraction layer.
    Default length of packets is 8192 bytes.
    '''
    def __handle_client(self, client_socket : socket.socket, event : Event, session_manager : SessionManager):
        client_socket.setblocking(False)
        sip = client_socket.getpeername()[0]
        while not event.is_set():
            try:
                request = client_socket.recv(runtime_conf['BUFFER_LEN'])
                if not request:
                    time.sleep(0.01)
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
                time.sleep(0.05)
                continue
        self.logger.debug("Halting session %s ..." % sip)
        session_manager.halt_session(sip)

    '''
    This method is passed as a invokeable to isolated thread scope so writing and reading of TCP packets is isolated one from each other.
    '''
    def __handle_buffer_out(self, logger : Logger, session_manager : SessionManager):
        while not self.keep_running.is_set():
            session_manager.handle_buffer_out()
            time.sleep(1)
        self.logger.debug("BufferHandler exiting, because server has been stopped!")

    def __create_marker_file__(self) -> None:
        marker_file_name = 'exit.lock'
        with open(marker_file_name, "+a") as f:
            f.write(str(datetime.datetime.now()))
    
    def __cleanup_marker_file(self) -> None:
        marker_file_name = 'exit.lock'
        os.remove(marker_file_name) 

    '''
    This method allows to launch the Server class instance, it can be called only once per Server instance.
    It allows to launch server using vhost configs including TLS support.
    '''
    def launch(self, vconfig : dict):
        if "persistent_sessions" in modules_config["ENABLED"]:
            self.__session_manager = SessionManager(MODULE_REFS["mod_persistent_sessions"])
        else:
            self.__session_manager = SessionManager()

        buffer_handler = threading.Thread(target = self.__handle_buffer_out, 
                                          args=(self.logger,
                                                self.__session_manager,), 
                                                name="Buffer_Writer", 
                                                daemon=True
                                          )
        buffer_handler.start()
        socket_thread = threading.Thread(target = launch_server, 
                                         args=(f"/tmp/{vhost['HOST']}_{vhost['PORT']}.sock", 
                                            logger, 
                                            self.__session_manager, 
                                            self.keep_running), 
                                         name="ConsoleSocketThread", 
                                         daemon=True
                                         )
        socket_thread.start()
        client_handler = None
        if runtime_conf['CRASH_RECOVERY']:
            self.__create_marker_file__()
        while True:
            client = None
            addr = None
            try:
                if not self.keep_running.is_set():
                    client, addr = self.__server.accept()
            except Exception as e:
                time.sleep(0.05)
            finally:
                if self.keep_running.is_set():
                    self.__server.shutdown(socket.SHUT_RDWR)
                    self.__server.close()
                    self.logger.info("Server received halt command, halting...")
                    break
            if not client and not addr:
                continue
            self.logger.info("Active Thread Count: %s" % threading.active_count())
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
            client_handler = threading.Thread(target = self.__handle_client, args=(client, s.lock_event(), self.__session_manager), name="SocketHandler%s" % (addr[0]), daemon=True)
            client_handler.start()  
        self.logger.info("Server main loop stopped! Awaiting some time to check whether workers exited as well.")
        time.sleep(1)
        self.logger.debug(f"{buffer_handler.name} - Is Alive: {buffer_handler.is_alive()} - Is Daemon: {buffer_handler.daemon}")
        self.logger.debug(f"{socket_thread.name} - Is Alive: {socket_thread.is_alive()} - Is Daemon: {socket_thread.daemon}")
        self.logger.info(f"It seems that server exits gracefully, removing exit.lock file.")
        self.__cleanup_marker_file()
# Just an entrypoint
if __name__ == '__main__':
    module_loader = ModuleLoader()
    module_loader.load_all(MODULE_REFS)
    for vhost in net_conf["VHOSTS"]:
        logger = Logger()
        server = Server(vhost, logger)
        server.launch(vhost)
    