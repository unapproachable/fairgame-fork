import json
import os
import time

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from stores.base_store import DEFAULT_REFRESH_DELAY
from stores.selenium_store import SeleniumStore
from utils import selenium_utils
from utils.logger import log

AMAZON_STORE_CONFIG = "config/amazon_config.json"
WISHLIST_URL = "/hz/wishlist/ls/"


class AmazonWishlist(SeleniumStore):

    def __init__(self, *args, notification_handler=None, detailed=None, no_screenshots=None, slow_mode=None,
                 no_image=None, disable_presence=None, log_stock_check=None, headless=None, **kwargs):
        super().__init__(*args, notification_handler=notification_handler, detailed=detailed,
                         no_screenshots=no_screenshots, slow_mode=slow_mode, no_image=no_image,
                         disable_presence=disable_presence, log_stock_check=log_stock_check, headless=headless,
                         **kwargs)
        log.info("Amazon Wishlist: Started")
        self.amazon_website = None
        self.wishlist_id = None
        # Load the config file to get the wishlist URL
        self.load_wishlist_config(AMAZON_STORE_CONFIG)
        self.wishlist_url = f"https://{self.amazon_website}{WISHLIST_URL}{self.wishlist_id}"

    def run(self, delay=DEFAULT_REFRESH_DELAY, test=False):
        # Get the driver
        log.info("Spawing web browser...")
        self.driver = self.get_driver(self.global_config.get_browser_profile_path())
        # Store the pids for clean shutdown
        self.webdriver_child_pids = selenium_utils.get_webdriver_pids(self.driver)

        # Get the wishlist
        log.info(f"Loading wishlist from {self.wishlist_url}")
        self.driver.get(self.wishlist_url)

        # Establish the Waiting Strategy
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='navFooter']")))

        log.info("Scrolling to load all wishlist items...")
        # Scroll to the bottom to load all items
        SCROLL_PAUSE_TIME = 1.5

        # Get scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)

            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height


        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='endOfListMarker']")))

        # Scroll back to the top
        self.driver.execute_script("window.scrollTo(0, 0);")


        # Product lookup: //div[contains(@class, 'g-item-details')]
        # Product ASIN lookup: .//div/@data-csa-c-item-type='asin'
        # Product name lookup: .//a[@class='a-link-normal']
        # Product price lookup: .//span[@class='a-offscreen']

        log.info("Parsing items...")
        config = {}
        item_list = []
        config["itemList"] = item_list
        item_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'g-item-details')]")
        log.info(f"Found {len(item_elements)} items.")
        for item_element in item_elements:
            # See ths link for syntax on finding elements within an element.  TL;DR is you have to
            # start the XPATH relative to the element you are searching (e.g. ".//"
            # https://www.selenium.dev/documentation/webdriver/elements/finders/#find-elements-from-element
            item = {}
            # Extract the ASIN
            asin_element = item_element.find_element(By.XPATH,".//div[@data-csa-c-item-type='asin']" )
            item["asins"] = asin_element.get_attribute("data-csa-c-item-id")
            # Extract the name
            name_element = item_element.find_element(By.XPATH,".//a[@class='a-link-normal']")
            item["name"] = name_element.text
            # Extract current selling price
            try:
                price_element = item_element.find_element(By.XPATH,".//span[@class='a-offscreen']")
                if price_element:
                    item["price"] = price_element.get_attribute("innerText")
            except NoSuchElementException:
                # Ignore, since not all items have a price on the wishlist page... because reasons?
                pass
            item_list.append(item)
        config_filename = f"config/amazon_{self.wishlist_id}.json"
        log.info(f"Writing configuration to {config_filename}")
        json.dump(config, open(config_filename,"w"), indent=4)
        log.info("Done")


    # Load the wishlist config file:
    def load_wishlist_config(self, amazon_config_path):
        """Mechanism to load and parse the asin, max, and min prices found in the itemList node of the specified JSON file

        Supported Nodes:
            itemList: consists of asin, min, and max prices)
            amazon_website: the root domain you want ot scan (e.g. www.amazon.com, www.amazon.de, etc.)

        """
        if os.path.exists(amazon_config_path):
            with open(amazon_config_path) as json_file:
                try:
                    config = json.load(json_file, )
                    self.amazon_website = config.get("amazon_website", "amazon.com")

                    if not config["wishlist_id"]:
                        log.error(f"AmazonWishlist config file is missing a wishlist_id")
                        exit(-1)

                    self.wishlist_id = config["wishlist_id"]

                    log.info("Found Wishlist ID: " + self.wishlist_id)

                except Exception as e:
                    log.error(f"{e} is missing")
                    log.error(
                        "amazon_config.json file not formatted properly: https://github.com/Hari-Nagarajan/fairgame/wiki/Usage#json-configuration"
                    )
                    exit(0)
        else:
            log.error(
                "No config file found, see here on how to fix this: https://github.com/Hari-Nagarajan/fairgame/wiki/Usage#json-configuration"
            )
            exit(0)

    def __del__(self):
        self.delete_driver()