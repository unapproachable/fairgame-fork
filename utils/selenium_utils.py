#      FairGame - Automated Purchasing Program
#      Copyright (C) 2021  Hari Nagarajan
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU General Public License for more details.
#
#      You should have received a copy of the GNU General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#      The author may be contacted through the project's GitHub, at:
#      https://github.com/Hari-Nagarajan/fairgame
import fileinput
import os
from logging import WARNING as logging_WARNING

import psutil
import requests
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from urllib3.connectionpool import log as urllib_logger

selenium_logger.setLevel(logging_WARNING)
urllib_logger.setLevel(logging_WARNING)


class AnyEc:
    """Use with WebDriverWait to combine expected_conditions
    in an OR.
    """

    def __init__(self, *args):
        self.ecs = args

    def __call__(self, driver):
        for fn in self.ecs:
            try:
                if fn(driver):
                    return True
            except:
                pass


def wait_for_element(d, e_id, time=30):
    """
    Uses webdriver(d) to wait for page title(title) to become visible
    """
    return WebDriverWait(d, time).until(ec.presence_of_element_located((By.ID, e_id)))


def wait_for_element_by_xpath(d, e_path, time=30):
    return WebDriverWait(d, time).until(
        ec.presence_of_element_located((By.XPATH, e_path))
    )


def wait_for_element_by_class(d, e_class, time=30):
    """
    Uses webdriver(d) to wait for page title(title) to become visible
    """
    return WebDriverWait(d, time).until(
        ec.presence_of_element_located((By.CLASS_NAME, e_class))
    )


def wait_for_title(d, title, path):
    """
    Uses webdriver(d) to navigate to get(path) until it equals title(title)
    """
    while d.title != title:
        d.get(path)
        WebDriverWait(d, 1000)


def wait_for_page(d, title, time=30):
    """
    Uses webdriver(d) to wait for page title(title) to become visible
    """
    WebDriverWait(d, time).until(ec.title_is(title))


def wait_for_either_title(d, title1, title2, time=30):
    """
    Uses webdriver(d) to wait for page title(title1 or title2) to become visible
    """
    try:
        WebDriverWait(d, time).until(AnyEc(ec.title_is(title1), ec.title_is(title2)))
    except Exception:
        pass


def wait_for_any_title(d, titles, time=30):
    """
    Uses webdriver(d) to wait for page title(any in the list of titles) to become visible
    """
    WebDriverWait(d, time).until(AnyEc(*[ec.title_is(title) for title in titles]))


def button_click_using_xpath(d, xpath):
    """
    Uses webdriver(d) to click a button using an XPath(xpath)
    """
    button_menu = WebDriverWait(d, 10).until(
        ec.element_to_be_clickable((By.XPATH, xpath))
    )
    action = ActionChains(d)
    action.move_to_element(button_menu).pause(1).click().perform()


def field_send_keys(d, field, keys):
    """
    Uses webdriver(d) to fiend a field(field), clears it and sends keys(keys)
    """
    elem = d.find_element_by_name(field)
    elem.clear()
    elem.send_keys(keys)


def has_class(element, class_name):
    classes = element.get_attribute("class")

    return class_name in classes


def add_cookies_to_session_from_driver(driver, session):
    cookies = driver.get_cookies()

    [
        session.cookies.set_cookie(
            requests.cookies.create_cookie(
                domain=cookie["domain"],
                name=cookie["name"],
                value=cookie["value"],
            )
        )
        for cookie in cookies
    ]


def enable_headless(options: Options):
    options.add_argument("--headless")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")


def create_selenium_directories():
    if not os.path.exists("screenshots"):
        try:
            os.makedirs("screenshots")
        except:
            raise
    if not os.path.exists("html_saves"):
        try:
            os.makedirs("html_saves")
        except:
            raise


def get_driver_options():
    options = Options()
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option("useAutomationExtension", False)
    # CHROME ONLY option to prevent Restore Session popup
    options.add_argument("--disable-session-crashed-bubble")
    return options


def cleanup_driver_crash_files(path_to_profile):
    # Delete crashed, so restore pop-up doesn't happen
    path_to_prefs = os.path.join(
        path_to_profile,
        "Default",
        "Preferences",
    )
    try:
        with fileinput.FileInput(path_to_prefs, inplace=True) as file:
            for line in file:
                print(line.replace("Crashed", "none"), end="")
    except FileNotFoundError:
        pass


def get_webdriver_pids(driver: ChromiumDriver):
    pid = driver.service.process.pid
    driver_process = psutil.Process(pid)
    children = driver_process.children(recursive=True)
    webdriver_child_pids = []
    for child in children:
        webdriver_child_pids.append(child.pid)
    return webdriver_child_pids
