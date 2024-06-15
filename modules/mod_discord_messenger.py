import requests
from config import MODULES
from logger import Logger

MODULE_NAME = "discord_messenger"


def __mod_init__(params: dict = None):
    if params:
        logger: Logger = params['logger']
        return DiscordMessenger(logger)
    return DiscordMessenger()


class DiscordMessenger:
    def __init__(self, logger : Logger) -> None:
        self.mUrl = MODULES['MODULES_CONFIG']['discord_messenger']['mUrl']
        self.logger: Logger = logger
    
    def send_to_webhook(self, message: str):
        data = {"content": message}
        response = requests.post(self.mUrl, json=data)
        if response.ok:
            self.logger.info("The status message was sent to Discord Hook.")
