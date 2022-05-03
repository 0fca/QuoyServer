from sys import stderr, stdout
from datetime import date

class Logger():
    def __init__(self, std_file_pipe  = None, err_file_pipe = None):
        self.err_file = err_file_pipe if err_file_pipe is not None else stderr
        self.std_file = std_file_pipe if std_file_pipe is not None else stdout
    
    def info(self, msg : str):
        d = date.today()
        print("~> [%s] %s" % (d.strftime("%d/%m/%Y %H:%M:%S"), msg), file=self.std_file)

    def err(self, msg):
        d = date.today()
        print("~> ! [%s] %s" % (d.strftime("%d/%m/%Y %H:%M:%S"), msg), file=self.err_file)
