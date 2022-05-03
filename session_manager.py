import logger
import server
import socket
import uuid

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
    
    def write_response_for(self, response : server.Response, username : str):
        if username in self.__buffer_out:
            self.__buffer_out[username].append(response)
        else:
            self.__buffer_out[username] = [response]

    def wipe_buffer(self):
        self.__buffer_out.clear()


class SessionManager():
    def __init__(self):
        self.session_queue : list[Session] = []

    def create(self, socket : socket.socket) -> Session:
        ip = socket.getpeername()[0]
        s = Session(ip)
        s.assing_socket(socket)
        filtered_sessions = list(filter(lambda s : (s.ip() == ip), self.session_queue))
        if not filtered_sessions:
            self.session_queue.append(s)
        return s