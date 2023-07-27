import socket

MODULE_NAME = "raw_health_check"
'''
This module is meant to allow TCP check of a host.
'''

def conn_check(host : str, port : int) -> bool:
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        err = client.connect_ex((host, port))
        return err == 0
    except:
        return False