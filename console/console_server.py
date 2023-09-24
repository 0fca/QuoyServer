import socket
import os
from logger import Logger
from multiprocessing import Event
from session_manager import SessionManager

socket_path = None

def halt_server(session_manager: SessionManager, keep_running: Event, logger: Logger):
    if not keep_running.is_set():
        for session in session_manager.existing_sessions():
            if session:
                session.lock_event().set()
            else:
                logger.debug(f"Skipping session which appeared as None")
        logger.debug("All halt events dispatched, stopping main server loop.")
        keep_running.set()

console_commands = {
    "halt": halt_server
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
            while True:
                data = connection.recv(256)
                if not data:
                    break
                logger.debug(f'Received data: {data.decode()}')
                # Generify this call
                # Move this to subfile
                console_commands[data.decode().strip()](session_manager=session_manager, keep_running=keep_running, logger=logger)
        finally:
            if keep_running.is_set():
                connection.close()
                os.unlink(socket_path)
    logger.debug("ConsoleSocketThread exited, because server has stopped.")

        