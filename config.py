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
        "discord_messenger",
        "raw_health_check",
        "users",
        "docker_stats"
    ],
    "MODULES_CONFIG": {
        "discord_messenger": {
            "mUrl": "https://discord.com/api/webhooks/1225936199324139660/6HQ-fuP_W7mP0yenZlO0-LMQDBSFtSEBGYdirV8ok82iRWteKng79HDUvZQfO25KsUNq"
        },
        "docker_stats":{
            "url": 'http://192.168.1.252:2375'
        }
    }
}
LOG_CONF = {
    "LOG_LEVEL": "Debug"
}
RUNTIME = {
    "CRASH_RECOVERY": True,
    "BUFFER_LEN": 8192,
    "LOCK_FILE": "exit.lock",
}