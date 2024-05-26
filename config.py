NET_CONF = {
    "VHOSTS" : [{
        "HOST" : '0.0.0.0',
        "PORT" : 27700,
        "TLS": False,
        "CERT_FILE": "base.cer",
        "KEY_FILE": "cert.key"
    }]
}
USER_CONF = {

}
DB_CONF = {
    "db_name": "user.db"
}
MODULES = {
    "MODULE_DIR": "./modules",
    "ENABLED": [
        "ssl",
        "persistent_sessions",
        "discord_messenger"
    ]
}
LOG_CONF = {
    "LOG_LEVEL": "Debug"
}
