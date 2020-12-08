import json
import random
import time
import webbrowser
from json.decoder import JSONDecodeError

import requests

from stores.basestore import BaseStoreHandler
from utils.logger import log

REALTIME_INVENTORY_URL = "https://www.bhphotovideo.com/bnh/controller/home/"
CONFIG_FILE_PATH = "config/bhphoto_config.json"

HEADERS = {
    "authority": "www.bhphotovideo.com",
    "accept": "application/json, text/plain, */*",
    "x-requested-with": "XMLHttpRequest",
    "x-csrf-token": "b8ce435519b0a57287ce6954e35246e1",
    "x-app-type": "desktop",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/87.0.4280.67 Safari/537.36",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": "https://www.bhphotovideo.com/find/wishlist.jsp?origSearch=wishlist",
    "accept-language": "en-US,en;q=0.9",
}


class BHPhotoHandler(BaseStoreHandler):
    def __init__(self, notification_handler) -> None:
        super().__init__()
        self.notification_handler = notification_handler
        self.wishlist_urls = []
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

    def run(self, delay=15):
        # Load real-time inventory for the provided SM list and clean it up as we go
        self.verify()
        message = "Starting to monitor Wishlists at B&H Store"
        log.info(message)
        self.notification_handler.send_notification(message)

        while True:
            for wishlist_url in self.wishlist_urls:
                wishlist_items = self.get_wishlist_items(wishlist_url)
                for item in wishlist_items:
                    if self.stock_checks > 0 and self.stock_checks % 1000 == 0:
                        checks_per_second = self.stock_checks / self.get_elapsed_time(
                            self.start_time
                        )
                        log.info(
                            f"Performed {self.stock_checks} stock checks so far ({checks_per_second} cps). Continuing "
                            f"to scan... "
                        )
                    if self.check_stock(item):
                        log.debug(f"Spawning browser to URL {wishlist_url}")
                        webbrowser.open_new(wishlist_url)
                        log.debug(f"Removing wishlist from hunt list.")
                        self.wishlist_urls.remove(wishlist_url)
                        self.notification_handler.send_notification(
                            f"Found in-stock item at B&H Photo: {wishlist_url}"
                        )
            time.sleep(delay + random.randint(1, 3))

    def parse_config(self):
        log.info(f"Processing config file from {CONFIG_FILE_PATH}")
        # Parse the configuration file to get our hunt list
        try:
            with open(CONFIG_FILE_PATH) as json_file:
                config = json.load(json_file)
                self.wishlist_urls = config.get("wishlist_urls")
        except FileNotFoundError:
            log.error(
                f"Configuration file not found at {CONFIG_FILE_PATH}.  Please see {CONFIG_FILE_PATH}_template."
            )
            exit(1)
        log.info(
            f"Found {len(self.wishlist_urls)} wishlists to track at B&H Photo store."
        )
        return len(self.wishlist_urls)

    def verify(self):
        log.info("Verifying wish lists...")
        total_items = 0
        for wishlist_url in self.wishlist_urls:
            wishlist_id = wishlist_url.split("/")[-2]
            # For each URL, get the session to set the coookies and then use the xhr request to get details
            if self.get_bh_web_session(wishlist_url):
                response_json = self.get_real_time_data(wishlist_id)
                log.info(
                    f"Found {response_json['itemCount']} items on '{response_json['name']}' to monitor."
                )
                for item in response_json["items"]:
                    total_items += 1
                    log.info(
                        f"Found '{item['shortDescription']}' listed as '{item['stockMessage']}' for {item['price']}"
                    )
            else:
                log.error(
                    "Failed to obtain a valid web-session from B&H Photo.  Unable to proceed."
                )
                exit(1)
        log.info(f"Verified {total_items} items on B&H Photo Wishlists")

    def get_bh_web_session(self, wishlist_url):
        url = wishlist_url
        """Request the specified Wishlist URL to populate the cookies"""
        log.debug("Initializing web session...")
        response = self.session.head(url)
        while response.is_redirect:
            # Wishlist URLs seem to generally be redirects, so follow it
            url = response.next.url
            log.debug(f"\tFollowing redirect to {url}")
            response = self.session.head(url)
        if wishlist_url != url:
            # Remap the URL for future requests
            log.debug(f"Removing Redirect URL: {wishlist_url}")
            idx = self.wishlist_urls.index(wishlist_url)
            self.wishlist_urls.remove(wishlist_url)
            log.debug(f"Adding redirected URL instead: {response.url}")
            self.wishlist_urls.insert(idx, response.url)
        if len(self.session.cookies) > 0:
            return True
        return False

    def get_wishlist_items(self, wishlist_url):
        if self.get_bh_web_session(wishlist_url):
            wishlist_id = wishlist_url.split("/")[-2]
            rtd = self.get_real_time_data(wishlist_id)
            if rtd:
                return rtd["items"]
            else:
                return []

    def get_real_time_data(self, wishlist_id):
        """B&H Photo website XHR request that we're borrowing for lightweight inventory queries.  Returns JSON"""
        log.debug(f"Calling B&H Photo web service...")
        try:
            parameters = {"Q": "json", "A": "wishListDetail", "li": wishlist_id}
            response_json = self.session.get(
                REALTIME_INVENTORY_URL,
                headers=HEADERS,
                params=parameters,
            ).json()
            return response_json
        except JSONDecodeError:
            log.error("Failed to receive valid JSON response.  Skipping")
            return json.loads("{}")

    def check_stock(self, item):
        price = item["price"]
        quantity = item["qtyReceived"]
        if item["available"]:
            log.info(
                f"B&H Photo has {quantity} of {item['shortDescription']} available to buy for {price}"
            )
            return True
        else:
            self.stock_checks += 1
        return False
