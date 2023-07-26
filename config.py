NET_CONF = {
    "VHOSTS" : [{
        "HOST" : '0.0.0.0',
        "PORT" : 27700,
        "TLS": False,
        "CERT_FILE": "base.cer",
        "KEY_FILE": "cert.key"
    }]
}
MODULES = {
    "MODULE_DIR": "./modules",
    "ENABLED": [
        "ssl"
    ]
}