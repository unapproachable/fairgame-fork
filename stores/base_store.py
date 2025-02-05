from abc import abstractmethod

from pypresence import exceptions as pyexceptions
from pypresence import presence

from common.globalconfig import GlobalConfig
from notifications.notifications import NotificationHandler
from utils import discord_presence as presence
from utils.logger import log

# Constants
DEFAULT_REFRESH_DELAY = 3


class BaseStore:
    def __init__(self,
                 *args,
                 global_config: GlobalConfig,
                 notification_handler: NotificationHandler,
                 detailed: bool,  # Refactor to verbose
                 single_shot: bool,  # One purchase and then quit
                 disable_presence: bool,  # Notifications
                 encryption_pass: str = None,  # Password for credentials file(?)
                 log_stock_check: bool,  # Could be rolled up in verbosity?
                 **kwargs
                 ):
        super().__init__(*args, **kwargs)
        self.global_config = global_config
        self.detailed = detailed
        self.disable_presence: bool = disable_presence
        self.encryption_pass: str = encryption_pass
        self.log_stock_check: bool = log_stock_check
        self.notification_handler: NotificationHandler = notification_handler
        self.single_shot: bool = single_shot
        self.testing: bool = False

        presence.enabled = not disable_presence

        try:
            presence.start_presence()
        except Exception in pyexceptions:
            log.error("Discord presence failed to load")
            presence.enabled = False

    @abstractmethod
    def run(self, delay=DEFAULT_REFRESH_DELAY, test=False):
        self.show_config()
        pass

    def show_config(self):
        if self.detailed:
            log.info(f"{'=' * 50}")
            attrs = vars(self)
            for item in attrs.items():
                key, value = item
                log.info(f"{key} = {value} [{type(value)}]")
            log.info(f"{'=' * 50}")
