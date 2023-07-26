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