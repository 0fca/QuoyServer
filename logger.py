from sys import stderr, stdout
from datetime import datetime
from config import LOG_CONF

class Logger():
    
    LEVELS = {
        "Trace": 0,
        "Debug": 1,
        "Info": 2,
        "Error": 3,
        "Severe": 4
    }
    
    def __init__(self, std_file_pipe  = None, err_file_pipe = None):
        self.err_file = err_file_pipe if err_file_pipe is not None else stderr
        self.std_file = std_file_pipe if std_file_pipe is not None else stdout
    
    def __print__(self, msg: str, level="Info", prefix="~>", file=None):
        if file is None:
            file = self.std_file
        configured_level = LOG_CONF["LOG_LEVEL"]
        if self.LEVELS[configured_level] <= self.LEVELS[level]: 
            d = datetime.now()
            print(f"{prefix} [%s] %s" % (d.strftime("%d/%m/%Y %H:%M:%S"), msg), file=file)
    
    def info(self, msg : str):
        self.__print__(msg);

    def err(self, msg):
        self.__print__(msg, level="Error", prefix="~> !", file=self.err_file)
    
    def debug(self, msg: str):
        self.__print__(msg, level="Debug", prefix="~> ?", file=self.std_file)
        
    def trace(self, msg: str):
        self.__print__(msg, level="Trace", prefix="~> ??", file=self.err_file)
        
    def severe(self, msg: str):
        self.__print__(msg, level="Severe", prefix="~> !!!", file=self.err_file)