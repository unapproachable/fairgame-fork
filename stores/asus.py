import json
import random
import webbrowser
import time
from json.decoder import JSONDecodeError

import requests

from stores.basestore import BaseStoreHandler
from utils.logger import log

ASUS_REALTIME_INVENTORY_URL = "https://store.asus.com/us/category/get_real_time_data"
CONFIG_FILE_PATH = "config/asus_config.json"

HEADERS = {
    "authority": "store.asus.com",
    "pragma": "no-cache",
    "cache-control": "no-cache",
    "accept": "application/json, text/javascript, */*; q=0.01",
    "x-requested-with": "XMLHttpRequest",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 "
                  "Safari/537.36",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://store.asus.com",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "accept-language": "en-US,en;q=0.9",
}


class AsusStoreHandler(BaseStoreHandler):
    def __init__(self, notification_handler) -> None:
        super().__init__()
        self.notification_handler = notification_handler
        self.sm_list = []
        self.stock_checks = 0
        self.start_time = int(time.time())

        # Load up our configuration
        self.parse_config()

        # Initialize the Session we'll use for this run
        self.session = requests.Session()

    def __del__(self):
        message = "Shutting down Asus Store Handler."
        log.info(message)
        self.notification_handler.send_notification(message)

    def run(self, delay=45):
        # Load real-time inventory for the provided SM list and clean it up as we go
        self.verify()
        message = "Starting to hunt SKUs at ASUS Store"
        log.info(message)
        self.notification_handler.send_notification(message)

        while True:
            status_list = self.get_sm_status_list() or []
            for sm_id, sm_details in status_list.items():
                if self.stock_checks > 0 and self.stock_checks % 1000 == 0:
                    checks_per_second = self.stock_checks / self.get_elapsed_time(
                        self.start_time
                    )
                    log.info(
                        f"Performed {self.stock_checks} stock checks so far ({checks_per_second} cps). Continuing to "
                        f"scan... "
                    )
                if self.check_stock(sm_details):
                    url = f"https://store.asus.com/us/item/{sm_id}"
                    log.debug(f"Spawning browser to URL {url}")
                    webbrowser.open_new(url)
                    log.debug(f"Removing {sm_id} from hunt list.")
                    self.sm_list.remove(sm_id)
                    self.notification_handler.send_notification(
                        f"Found in-stock item at ASUS: {url}"
                    )
            time.sleep(delay + random.randint(1, 3))

    def parse_config(self):
        log.info(f"Processing config file from {CONFIG_FILE_PATH}")
        # Parse the configuration file to get our hunt list
        try:
            with open(CONFIG_FILE_PATH) as json_file:
                config = json.load(json_file)
                self.sm_list = config.get("sm_list")
        except FileNotFoundError:
            log.error(
                f"Configuration file not found at {CONFIG_FILE_PATH}.  Please see {CONFIG_FILE_PATH}_template."
            )
            exit(1)
        log.info(f"Found {len(self.sm_list)} SM numbers to track at the ASUS store.")

    def verify(self):
        log.info("Verifying item list...")
        sm_status_list = self.get_sm_status_list()
        for sm_id, sm_details in sm_status_list.items():
            if sm_details["not_found"]:
                log.error(
                    f"ASUS store reports {sm_id} not found.  Removing {sm_id} from list"
                )
                # Remove from the list, since ASUS reports it as "not found"
                self.sm_list.remove(sm_id)
            else:
                name = sm_details["market_info"]["name"]
                stop_index = name.index(" (")
                short_name = name[0:stop_index]
                log.info(
                    f"Found {sm_id}: {short_name} @ {sm_details['market_info']['price']['final_price']['price']}"
                )
        log.info(f"Verified {len(self.sm_list)} items on Asus Store")

    def get_sm_status_list(self):
        # Get the list of SM responses or an empty response
        rtd = self.get_real_time_data()
        if rtd:
            return rtd["data"]
        else:
            return []

    def get_real_time_data(self):
        """ASUS website XHR request that we're borrowing for lightweight inventory queries.  Returns JSON"""
        log.debug(f"Calling ASUS web service with {len(self.sm_list)} items.")
        payload = {"sm_seq_list[]": self.sm_list}
        try:
            response_json = self.session.post(
                ASUS_REALTIME_INVENTORY_URL, headers=HEADERS, data=payload
            ).json()
            return response_json
        except JSONDecodeError:
            log.error("Failed to receive valid JSON response.  Skipping")
            return json.loads("{}")

    def check_stock(self, item):
        price = item["market_info"]["price"]["final_price"]["price"]
        quantity = item["market_info"]["quantity"]
        if item["market_info"]["buy"]:
            log.info(
                f"Asus has {quantity} of {item['sm_seq']} available to buy for {price}"
            )
            return True
        else:
            # log.info(f"{sm_id} is unavailable.  Offer price listed as {price}")
            self.stock_checks += 1
        return False
