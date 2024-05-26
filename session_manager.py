import logger
import socket
import uuid
import json

from modules.mod_persistent_sessions import Sessions, PersistentSession
from threading import Event, Thread

class Response():
    def __init__(self, payload : str):
        self.__payload = payload

    def to_str(self, enc : str = "ASCII") -> bytes:
        return bytes(self.__payload + "\r\n", enc)

class Session():
    def __init__(self, ip : str, event : Event):
        self.__sid = uuid.uuid4().hex
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
        # In case that user has something in a buffer at the moment of writing another response to the queue, 
        # we just want to append a response instead of overwriting it
        if username in self.__buffer_out:
            self.__buffer_out[username].append(response)
        else:
            self.__buffer_out[username] = [response]

    def wipe_buffer(self):
        self.__buffer_out.clear()
    
    def __str__(self) -> str:
        return f"{self.__username if self.__username else 'Not registered client'} on {self.__ip}"


class SessionManager():
    def __init__(self, mod_ref = None):
        self.__session_queue : list[Session] = []
        self.logger = logger.Logger()
        self.server_halted = False
        self.sessions : Sessions = None
        if mod_ref is not None:
            mod_init_func = getattr(mod_ref, "__mod_init__")
            self.sessions = mod_init_func()
            self.logger.info("SessionManager loaded with persistent session support (SQLite)")

    def create(self, socket : socket.socket) -> Session:
        ip = socket.getpeername()[0]
        event = Event()
        s = Session(ip, event)
        s.assing_socket(socket)
        s.assign_user(s.sid())
        filtered_sessions = list(filter(lambda s : (s.ip() == ip), self.__session_queue))
        # FIXME: This piece of code works, however it should handle this situation in some other way: 
        # returning some meaningful value determining an error or throwing an except
        if not filtered_sessions:
            self.__session_queue.append(s)
            self.__update_session_store__()

        return s

    def existing_session_by_username(self, username : str) -> Session:
        sessions : Session = list(filter(lambda s : (s.username() == username), self.__session_queue))

        return sessions[0] if len(sessions) > 0 else None
    
    def existing_session_by_ip(self, ip : str) -> Session:
        sessions: list[Session] = list(filter(lambda s : (s.ip() == ip), self.__session_queue))
        return sessions[0] if len(sessions) == 1 else None

    def existing_session_by_sid(self, sid : str) -> Session:
        session : Session = list(filter(lambda s : (s.sid() == sid), self.__session_queue))
        return session
    
    def existing_sessions(self) -> list[Session]:
        return self.__session_queue
    
    def remove_session(self, session : Session):
        self.logger.debug("Removing session %s" % (session.ip()))
        self.sessions.forget_session(session.sid())
        self.__session_queue.remove(session)
        del session
    
    def __update_session_store__(self) -> None:
        if self.__session_queue:
            for queued_session in self.__session_queue:
                session = self.sessions.find_by_id(queued_session.username())
                if session is None:
                    self.sessions.append_session(queued_session)

    def __single_session_update(self, session: Session) -> None:
        self.sessions.append_session(session)

    '''
    This method handles writing to the out buffer of server for each user session.
    It uses a concept of event lock objects to properly handle access to a session object. 
    It is in case of writing and reading between worker threads at the same time.
    '''
    def handle_buffer_out(self):
        # Go through all existing sessions
        for session in self.existing_sessions():
                socket = session.socket()
                if session and session.username():
                    # As of a fact that buffer out is actually shared between all sessions, 
                    # we need to find all the messages for current session. 
                    for msg in session.read_all_for_username(session.username()):
                        try:
                            self.logger.debug("Writing %s to socket of %s" % (msg.to_str(), session.username()))
                            socket.sendall(bytes(msg.to_str()))
                        except OSError as e:
                            # There was an OS level error of networking layer, handle it by removing session and closing a socket
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
                        # Buffer is of one time use - we need to clean it up, 
                        # so the commands wont get stacked there and wont get sent twice or more times
                        session.wipe_buffer()
    
    def halt_session(self, sip : str):
        sessions : list[Session] = list(filter(lambda s : (s.ip() == sip), self.__session_queue))
        if sessions and sessions[0] in self.__session_queue:
            self.remove_session(sessions[0])

    def update_session(self, sid: str):
        sessions : list[Session] = list(filter(lambda s : (s.sid() == sid), self.__session_queue))
        if sessions and sessions[0]:
            self.__single_session_update(sessions[0])
