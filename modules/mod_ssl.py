from logger import Logger
import ssl
import os

MODULE_NAME = "ssl"
'''
This module is creates a proper client object for a raw TCP socket wrapped up with SSLContext layer.
In other words, it allows server to communicate with clients using TLSv1.2
'''
def __mod_init__(params: dict):
    # FIXME: This should be parametrized
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    if os.path.isfile(params['certfile']) and os.path.isfile(params["keyfile"]):
        context.load_cert_chain(certfile=params["certfile"], keyfile=params["keyfile"])
        client = context.wrap_socket(client, server_side=True)
        return client
    else:
        raise Exception("The configuration is invalid, the cert file and a key file cannot be empty prior to set up SSL server socket")