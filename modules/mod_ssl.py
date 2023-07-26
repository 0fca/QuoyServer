from logger import Logger
import ssl
import os

MODULE_NAME = "ssl"

def __mod_init__(params: dict):
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    if os.path.isfile(params['certfile']) and os.path.isfile(params["keyfile"]):
        context.load_cert_chain(certfile=params["certfile"], keyfile=params["keyfile"])
        client = context.wrap_socket(client, server_side=True)
        return client
    else:
        raise Exception("The configuration is invalid, the cert file and a key file cannot be empty prior to set up SSL server socket")