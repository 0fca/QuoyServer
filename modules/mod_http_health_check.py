import requests

MODULE_NAME = "http_health_check"

'''
This module is meant to allow HTTP check of a host.
'''

def conn_check(addr: str, port: int, proto="https"):
    r = requests.get(f"{proto}://{addr}:{port}/Health")
    if r.status_code == 200:
        sanitized = r.text.strip()
        return sanitized.lower() == "healthy"