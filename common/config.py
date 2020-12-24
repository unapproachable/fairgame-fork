import os
import config
import stdiomask

from utils.encryption import load_encrypted_config, create_encrypted_config
from utils.logger import log

GLOBAL_CONFIG_FILE = "config/fairgame.conf"
AMAZON_CREDENTIAL_FILE = "config/amazon_credentials.json"


def await_credential_input():
    username = input("Amazon login ID: ")
    password = stdiomask.getpass(prompt="Amazon Password: ")
    return {
        "username": username,
        "password": password,
    }


def get_credentials(credentials_file, encrypted_pass=None):
    if os.path.exists(credentials_file):
        credential = load_encrypted_config(credentials_file, encrypted_pass)
        return credential["username"], credential["password"]
    else:
        log.info("No credential file found, let's make one")
        log.info("NOTE: DO NOT SAVE YOUR CREDENTIALS IN CHROME, CLICK NEVER!")
        credential = await_credential_input()
        create_encrypted_config(credential, credentials_file)
        return credential["username"], credential["password"]


class Config:
    def __init__(self) -> None:
        super().__init__()
        log.info("Initializing Global configuration...")
        # Load up the global configuration
        self.global_config = config.Config(GLOBAL_CONFIG_FILE)
        # with open(GLOBAL_CONFIG_FILE) as json_config:
        #     self.global_config = json.load(json_config)

    def get_amazon_config(self):
        # TODO: Refactor this in case we still need a flag
        encryption_pass = None
        log.info("Initializing Amazon configuration...")
        # Load up all things Amazon
        amazon_config = self.global_config["AMAZON"]
        amazon_config["username"], amazon_config["password"] = get_credentials(
            AMAZON_CREDENTIAL_FILE
        )
        return amazon_config
