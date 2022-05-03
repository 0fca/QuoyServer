from ssl import SSLSocket
import logger
import socket
import uuid
from threading import Event

class Response():
    def __init__(self, payload : str):
        self.__payload = payload

    def to_str(self, enc : str = "ASCII") -> bytes:
        return bytes(self.__payload + "\r\n", enc)

class Session():
    def __init__(self, ip : str, event : Event):
        self.__sid = uuid.uuid4()
        self.__ip = ip
        self.__socket = None
        self.__username = ""
        self.__buffer_out : dict[list] = {}
        self.event = event
    
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
    def lock_event(self) -> Event:
        return self.event
    
    def erase_lock(self):
        del self.event
    
    def write_response_for(self, response : Response, username : str):
        if username in self.__buffer_out:
            self.__buffer_out[username].append(response)
        else:
            self.__buffer_out[username] = [response]

    def wipe_buffer(self):
        self.__buffer_out.clear()


class SessionManager():
    def __init__(self):
        self.__session_queue : list[Session] = []
        self.logger = logger.Logger()

    def create(self, socket : socket.socket) -> Session:
        ip = socket.getpeername()[0]
        event = Event()
        s = Session(ip, event)
        s.assing_socket(socket)
        filtered_sessions = list(filter(lambda s : (s.ip() == ip), self.__session_queue))
        # FIXME: This piece of code works, however it should handle this situation in some other way: returning some other value or throwing an except
        if not filtered_sessions:
            self.__session_queue.append(s)
        return s

    def existing_session_by_username(self, username : str) -> Session:
        sessions : Session = list(filter(lambda s : (s.username() == username), self.__session_queue))
        return sessions[0] if len(sessions) > 0 else None
    
    def existing_session_by_ip(self, ip : str) -> Session:
        sessions: list[Session] = list(filter(lambda s : (s.ip() == ip), self.__session_queue))
        return sessions[0] if len(sessions) > 0 else None

    def existing_sessions(self) -> list[Session]:
        return self.__session_queue
    
    def remove_session(self, session : Session):
        self.logger.info("Removing session %s" % (session.username()))
        self.__session_queue.remove(session)
        del session

    def handle_buffer_out(self):
        for session in self.existing_sessions():
                socket : SSLSocket = session.socket()
                if session and session.username():
                    for msg in session.read_all_for_username(session.username()):
                        try:
                            self.logger.info("Writing %s to socket of %s" % (msg.to_str(), session.username()))
                            socket.sendall(bytes(msg.to_str()))
                        except OSError as e:
                            self.logger.err(e)
                            if session in self.existing_sessions():
                               self.remove_session(session)
                            socket.close()
                            if session.lock_event():
                                session.lock_event().set()
                                session.erase_lock()
                        except Exception as e:
                            self.logger.err(str(e))
                            session.lock_event().set()
                    if session:
                        session.wipe_buffer()
    def halt_session(self, sip : str):
        sessions : list[Session] = list(filter(lambda s : (s.ip() == sip), self.__session_queue))
        if sessions and sessions[0] in self.__session_queue:
            self.remove_session(sessions[0])
