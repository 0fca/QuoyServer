import socket
import os
from logger import Logger
from multiprocessing import Event
from session_manager import SessionManager
from time import sleep

socket_path = None
encoding = "ASCII"

def __format_str__(msg: str):
    return msg+"\n"

def as_bytes(msg: str) -> bytes:
    return bytes(msg, encoding=encoding)

def __console_prompt__() -> str:
    return "\n~>"

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

def server_stat(sock_conn: socket, session_manager: SessionManager, keep_running: Event, logger: Logger):
    sock_conn.sendall(as_bytes(__format_str__(f"Current QUOY Server Status")))
    sessions = session_manager.existing_sessions()
    if not sessions:
        sock_conn.sendall(as_bytes(__format_str__(f"No active sessions")))
        sock_conn.sendall(as_bytes(__console_prompt__()))
        return
    for s in sessions:
        tmp = f"{s.ip()} as {s.username() if s.username() else '?'} using {s.socket().family}"
        sock_conn.sendall(as_bytes(tmp))
    sock_conn.sendall(as_bytes(f"{__console_prompt__()}"))



console_commands = {
    "halt": halt_server,
    "stat": server_stat
}
# TODO: Rewrite this using classes?

def launch_server(socket_file: str, logger : Logger, session_manager: SessionManager, keep_running: Event):
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
        connection, client_address = server.accept()

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
                console_commands[data.decode().strip()](sock_conn=connection, session_manager=session_manager, keep_running=keep_running, logger=logger)
        finally:
            connection.close()
            os.unlink(socket_path)
    logger.debug("ConsoleSocketThread exited, because server has stopped.")

        