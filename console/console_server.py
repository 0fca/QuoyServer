import socket
import os
from logger import Logger
from multiprocessing import Event
from session_manager import SessionManager, Session
from config import MODULES, RUNTIME

from typing import List
from zcached import ZCached, Result

socket_path = None
encoding = "ASCII"
modules = None
loaded_modules = {}
systems = {
    'PikaCore': ['core.lukas-bownik.net', 443], 
    'PikaNoteAPI': ['note.lukas-bownik.net', 443], 
    'PikaML': ['ml.lukas-bownik.net', 443]
}
system_protocols = {
    'PikaCore': ['TCP', 'HTTP'],
    'PikaNoteAPI': ['TCP'],
    'PikaML': ['TCP']
}

def __format_str__(msg: str):
    return msg+"\n"

def as_bytes(msg: str) -> bytes:
    return bytes(msg, encoding=encoding)

def __console_prompt__() -> str:
    return "\n~>"

def __adress_family__(s: Session) -> str:
    info = socket.getaddrinfo(s.ip(), s.socket().getpeername()[1], proto=s.socket().proto, family=s.socket().family)
    # info returns a list of tuples 
    # all sockets types for this object 
    # so we take first one and the first index in tuple - it is always AF object
    # AF object as string is in format: AddressFamily.AF_INET thus we split it by "."
    return str(info[0][0]).split(".")[1]


def check_raw_hc() -> str:
    if loaded_modules:
        return_message = 'Module appears to be not loaded'
        if 'mod_raw_health_check' in loaded_modules.keys():
            return_message = '\n'
            conn_check = getattr(loaded_modules['mod_raw_health_check'], 'conn_check')
            for system in systems:
                host = systems[system][0]
                port = systems[system][1]
                if conn_check(host, port):
                    return_message += f'{host} appears to be up\n'
                else:
                    return_message += f'{host} appears to be down\n'
        return return_message
    raise Exception("Modules were not passed to Console Server instance")

def check_if_ssl_enabled() -> str:
    if loaded_modules:
        if 'mod_ssl' in loaded_modules.keys():
            return "SSL mod is enabled for that instance"
        return "SSL mod is not enabled for that instance"
    raise Exception("Modules were not passed to Console Server instance")

def check_persistent_session_support() -> str:
    if loaded_modules:
        if 'mod_persistent_sessions' in loaded_modules.keys():
            with open(RUNTIME['LOCK_FILE'], mode='+r') as f:
                file_content = f.readline()
                return f"Persistent Sessions support is enabled\nTimestamp: {file_content}"
        return "Persistent Sessions support is disabled"
    raise Exception("Modules were not passed to Console Server Instance")

def halt_server(sock_conn: socket, session_manager: SessionManager, keep_running: Event, logger: Logger):
    if not keep_running.is_set():
        for session in session_manager.existing_sessions():
            if session:
                session.lock_event().set()
                sock_conn.sendall(as_bytes(__format_str__(f'Locking session: {session}')))
            else:
                logger.debug(f"Skipping session which appeared as None")
        logger.debug("All halt events dispatched, stopping main server loop.")
        keep_running.set()
        sock_conn.sendall(as_bytes('Server shall quit shortly... Goodbye!'))

def server_sessions(sock_conn: socket, session_manager: SessionManager, keep_running: Event, logger: Logger):
    if not keep_running.is_set():
        sock_conn.sendall(as_bytes(__format_str__(f"Current QUOY Server Sessions")))
        sessions = session_manager.existing_sessions()
        if not sessions:
            sock_conn.sendall(as_bytes(__format_str__(f"No active sessions")))
            sock_conn.sendall(as_bytes(__console_prompt__()))
            return
        for s in sessions:
            tmp = f"{s.ip()} as {s.username() if s.username() else '?'} using {__adress_family__(s)}"
            sock_conn.sendall(as_bytes(__format_str__(tmp)))
        sock_conn.sendall(as_bytes(f"{__console_prompt__()}"))

def server_stat(sock_conn: socket, session_manager: SessionManager, keep_running: Event, logger: Logger):
    sock_conn.sendall(as_bytes(__format_str__(f"Current QUOY Server Status")))
    sessions = session_manager.existing_sessions()
    if not sessions:
        sock_conn.sendall(as_bytes(__format_str__(f"No active sessions")))
        sock_conn.sendall(as_bytes(__console_prompt__()))
        return
    for s in sessions:
        tmp = f"{s.ip()} as {s.username() if s.username() else '?'} using {__adress_family__(s)}"
        sock_conn.sendall(as_bytes(__format_str__(tmp)))
    sock_conn.sendall(as_bytes(f"{__console_prompt__()}"))
    if not keep_running.is_set():
        sock_conn.sendall(as_bytes(__format_str__(f"Current QUOY Server Status")))
        sock_conn.sendall(as_bytes(__format_str__(f"Status is being loaded, please wait...")))
        status_message = 'QUOY Server is running, but no information could be gathered.\nReason: {0}'
        try: 
            is_ssl_enabled = check_if_ssl_enabled()
            status_message = f'{__console_prompt__()}{__format_str__("**SSL Mod status**:")} {is_ssl_enabled}'
            http_raw_check = check_raw_hc()
            status_message += f'{__console_prompt__()}{__format_str__("**Raw Health Check Mod**:")} {http_raw_check}'
            persistent_sessions_enabled = check_persistent_session_support()
            status_message += f'{__console_prompt__()}{__format_str__("**Persistent Sessions Mod**:")} {persistent_sessions_enabled}'
        except Exception as e:
            status_message = status_message.format(e.args[0])
        if 'mod_discord_messenger' in loaded_modules.keys():
            mRef = loaded_modules['mod_discord_messenger']
            messenger = getattr(mRef, "__mod_init__")({'logger': logger})
            messenger.send_to_webhook(status_message)
        sock_conn.sendall(as_bytes(status_message))
        logger.debug("Sending message completed")
        sock_conn.sendall(as_bytes(f"{__console_prompt__()}"))

def exit_server(sock_conn: socket, session_manager: SessionManager, keep_running: Event, logger: Logger):
    sock_conn.sendall(as_bytes(__format_str__('To exit press Ctrl-C')))
    sock_conn.sendall(as_bytes(f"{__console_prompt__()}"))

def rsrc(sock_conn: socket, session_manager: SessionManager, keep_running: Event, logger: Logger):
    with ZCached(host="127.0.0.1", port=7556) as client:
        client.run()

        if client.is_alive() is False:
            sock_conn.sendall(as_bytes(__format_str__('Command unavailable due to zcached server inaccessibility')))
        # TODO: Save some markers to make global server command cron worker
        client.set(key="rsrc", value="run")
        client.save()
        client.flush()
        sock_conn.sendall(as_bytes(__format_str__('rsrc worker will run asap')))
    
    
console_commands = {
    "halt": halt_server,
    "sessions": server_sessions,
    "stat": server_stat,
    "exit": exit_server,
    "rsrc": rsrc
}
# TODO: Rewrite this using classes?

def load_configured_modules(modules: dict):
    if modules:
        for module in modules:
            if modules[module].MODULE_NAME in MODULES['ENABLED']:
                loaded_modules[module] = modules[module]

def launch_server(socket_file: str, logger : Logger, session_manager: SessionManager, keep_running: Event, opt_args: dict):
    if 'modules' in opt_args.keys():
        load_configured_modules(opt_args['modules'])
        logger.info("Modules has been passed as optional argument.")
    socket_path = socket_file
    if not socket_path:
        raise OSError("Cannot create a socket file for console server")
    try:
        os.unlink(socket_path)
    except OSError:
        logger.debug("Couldn't unlink socket, so it does not exist, proceeding...")
        pass
    while not keep_running.is_set():
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(socket_path)
        server.listen(1)
        logger.debug('Console Server is listening for incoming connections...')
        connection, client_address  = server.accept()

        try:
            logger.debug(f'Connection from {str(connection).split(", ")[0][-4:]}')
            connection.sendall(as_bytes(__format_str__('QUOY Server Console')))
            connection.sendall(as_bytes(__console_prompt__()))
            while True:
                data = connection.recv(256)
                if not data:
                    break
                logger.debug(f'Console Server received data: {data.decode()}')
                # Generify this call
                # Move this to subfile
                cmd_input = data.decode().strip()
                if cmd_input in console_commands:
                    console_commands[cmd_input](sock_conn=connection, session_manager=session_manager, keep_running=keep_running, logger=logger)
        finally:
            connection.close()
            os.unlink(socket_path)
    logger.debug("ConsoleSocketThread exited, because server has stopped.")

        