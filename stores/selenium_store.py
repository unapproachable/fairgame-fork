import platform
import time
from contextlib import contextmanager
from datetime import datetime

import psutil
from selenium import webdriver
from selenium.common import exceptions as sel_exceptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.options import PageLoadStrategy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from notifications.notifications import NotificationHandler
from stores.base_store import BaseStore
from utils import selenium_utils
from utils.logger import log

DEFAULT_PAGE_WAIT_DELAY = 0.5  # also serves as minimum wait for randomized delays
DEFAULT_MAX_PAGE_WAIT_DELAY = 1.0  # used for random page wait delay
DEFAULT_MAX_TIMEOUT = 10

# noinspection DuplicatedCode
def get_timeout(timeout=DEFAULT_MAX_TIMEOUT):
    return time.time() + timeout


class SeleniumStore(BaseStore):


    def __init__(self, *args, notification_handler: NotificationHandler, detailed: bool, no_screenshots: bool,
                 slow_mode: bool, no_image: bool, single_shot: bool = False, disable_presence: bool, log_stock_check: bool,
                 headless: bool = False, **kwargs):
        super().__init__(*args, notification_handler=notification_handler, detailed=detailed, single_shot=single_shot,
                         disable_presence=disable_presence, log_stock_check=log_stock_check, **kwargs)
        self.headless: bool = headless
        self.no_image: bool = no_image
        self.slow_mode: bool = slow_mode
        self.take_screenshots = not no_screenshots

        self.driver : WebDriver = None
        self.profile_path = self.global_config.get_browser_profile_path()
        self.webdriver_child_pids = []
        self.webdriver_initialized = False

        selenium_utils.create_selenium_directories()

        self.profile_path = self.global_config.get_browser_profile_path()

    def create_drive(self, path_to_profile) -> bool:
        driver = get_driver(self, path_to_profile)
        if driver:
            self.driver = driver
            self.webdriver_child_pids = selenium_utils.get_webdriver_pids(self.driver)
            return True
        return False

    def get_driver(self, path_to_profile):

        selenium_utils.cleanup_driver_crash_files(path_to_profile)

        # Load generic scraping driver options
        driver_options = selenium_utils.get_driver_options()

        if not self.webdriver_initialized:
            self.configure_webdriver(path_to_profile, driver_options)

        try:
            driver = webdriver.Chrome(
                options=driver_options,
                service=ChromeService(ChromeDriverManager().install())
            )
        except Exception as e:
            log.error(e)
            log.error(
                "If you have a JSON warning above, try cleaning your profile (e.g. --clean-profile)"
            )
            log.error(
                "If that's not it, you probably have a previous Chrome window open. You should close it."
            )

            return
        return driver

    def configure_webdriver(self, path_to_profile, options):
        # See https://developer.chrome.com/docs/chromedriver/capabilities#recognized_capabilities
        prefs = {
            "profile.password_manager_enabled": False,
            "credentials_enable_service": False,
        }
        if self.no_image:
            prefs["profile.managed_default_content_settings.images"] = 2
        else:
            prefs["profile.managed_default_content_settings.images"] = 0
        # See https://www.selenium.dev/documentation/webdriver/drivers/options/#pageloadstrategy

        if self.slow_mode:
            options.page_load_strategy = PageLoadStrategy.normal
        else:
            options.page_load_strategy = PageLoadStrategy.none
        if self.headless:
            selenium_utils.enable_headless(options)

        options.add_experimental_option("prefs", prefs)
        options.add_argument(f"user-data-dir={path_to_profile}")
        self.webdriver_initialized = True

    def delete_driver(self):
        try:
            if platform.system() == "Windows" and self.driver:
                log.info("Cleaning up after web driver...")
                # brute force kill child Chrome pids with fire
                for pid in self.webdriver_child_pids:
                    try:
                        log.debug(f"Killing {pid}...")
                        process = psutil.Process(pid)
                        process.kill()
                    except psutil.NoSuchProcess:
                        log.debug(f"{pid} not found. Continuing...")
                        pass
            elif self.driver:
                self.driver.quit()

        except Exception as e:
            log.info(e)
            log.info(
                "Failed to clean up after web driver.  Please manually close browser."
            )
            return False
        return True

    def save_screenshot(self, page):
        file_name = get_timestamp_filename("screenshots/screenshot-" + page, ".png")
        try:
            self.driver.save_screenshot(file_name)
            return file_name
        except sel_exceptions.TimeoutException:
            log.info("Timed out taking screenshot, trying to continue anyway")
            pass
        except Exception as e:
            log.error(f"Trying to recover from error: {e}")
            pass
        return None

    def save_page_source(self, page):
        """Saves DOM at the current state when called.  This includes state changes from DOM manipulation via JS"""
        file_name = get_timestamp_filename("html_saves/" + page + "_source", "html")

        page_source = self.driver.page_source
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(page_source)

    @contextmanager
    def wait_for_page_content_change(self, timeout=5):
        """Utility to help manage selenium waiting for a page to load after an action, like a click"""
        old_page = self.driver.find_element(By.TAG_NAME, "html")
        yield
        try:
            WebDriverWait(self.driver, timeout).until(EC.staleness_of(old_page))
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//title"))
            )
        except sel_exceptions.TimeoutException:
            log.info("Timed out reloading page, trying to continue anyway")
            pass
        except Exception as e:
            log.error(f"Trying to recover from error: {e}")
            pass
        return None

    def wait_for_page_change(self, page_title, timeout=3):
        time_to_end = get_timeout(timeout=timeout)
        while time.time() < time_to_end and (
                self.driver.title == page_title or not self.driver.title
        ):
            pass
        if self.driver.title != page_title:
            return True
        else:
            return False

    def page_wait_delay(self):
        return DEFAULT_PAGE_WAIT_DELAY

    def send_notification(self, message, page_name, take_screenshot=True):
        if take_screenshot:
            file_name = self.save_screenshot(page_name)
            self.notification_handler.send_notification(message, file_name)
        else:
            self.notification_handler.send_notification(message)

def wait_for_element_by_xpath(d, xpath, timeout=10):
    try:
        WebDriverWait(d, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
    except sel_exceptions.TimeoutException:
        log.error(f"failed to find {xpath}")
        return False

    return True

def get_timestamp_filename(name, extension):
    """Utility method to create a filename with a timestamp appended to the root and before
    the provided file extension"""
    now = datetime.now()
    date = now.strftime("%m-%d-%Y_%H_%M_%S")
    if extension.startswith("."):
        return name + "_" + date + extension
    else:
        return name + "_" + date + "." + extension

def join_xpaths(xpath_list, separator=" | "):
    return separator.join(xpath_list)
