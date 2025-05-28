import os
import pickle
from .utils import get_logger, get_config

class SessionManager:
    def __init__(self, username):
        self.username = username
        self.logger = get_logger()
        self.config = get_config()
        cookies_base_path = self.config.get('SessionManagement', 'cookies_path', fallback='.cookies/')
        if not os.path.exists(cookies_base_path):
            os.makedirs(cookies_base_path)
        self.cookie_file_path = os.path.join(cookies_base_path, f"{self.username}_cookies.pkl")
        # self.encrypt_cookies = self.config.getboolean('SessionManagement', 'encrypt_cookies', fallback=False)
        # if self.encrypt_cookies: # Add encryption/decryption logic if needed
        #     self.logger.info("Cookie encryption enabled (placeholder).")

    def save_cookies(self, driver):
        try:
            cookies = driver.get_cookies()
            with open(self.cookie_file_path, 'wb') as f:
                pickle.dump(cookies, f)
            self.logger.info(f"Session cookies saved for {self.username} to {self.cookie_file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save cookies for {self.username}: {e}")

    def load_cookies(self, driver):
        if not os.path.exists(self.cookie_file_path):
            self.logger.info(f"No cookie file found for {self.username} at {self.cookie_file_path}")
            return False
        try:
            with open(self.cookie_file_path, 'rb') as f:
                cookies = pickle.load(f)
            
            # Instagram might require current domain for cookies. Navigate first.
            base_url = self.config.get('GeneralSettings', 'base_url', fallback="https://www.instagram.com")
            if not driver.current_url.startswith(base_url):
                driver.get(base_url + "/") # Go to a valid IG page before adding cookies
                from .anti_detection import human_delay # Local import to avoid circularity
                human_delay("navigation")

            for cookie in cookies:
                # Selenium sometimes has issues with 'expiry' float vs int
                if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                    cookie['expiry'] = int(cookie['expiry'])
                # Ensure cookie domain is valid if IG becomes stricter
                # if 'domain' in cookie and not cookie['domain'].endswith('.instagram.com'):
                #     continue # Skip cookies not for instagram.com
                try:
                    driver.add_cookie(cookie)
                except Exception as e_add:
                    self.logger.debug(f"Could not add cookie {cookie.get('name')}: {e_add}")
            self.logger.info(f"Loaded {len(cookies)} cookies for {self.username}.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load cookies for {self.username}: {e}")
            # Corrupted cookie file? Delete it.
            try:
                os.remove(self.cookie_file_path)
                self.logger.info(f"Removed potentially corrupted cookie file: {self.cookie_file_path}")
            except OSError:
                pass
            return False

    def clear_cookies(self):
        if os.path.exists(self.cookie_file_path):
            try:
                os.remove(self.cookie_file_path)
                self.logger.info(f"Cleared cookies for {self.username} from {self.cookie_file_path}")
            except OSError as e:
                self.logger.error(f"Failed to clear cookies for {self.username}: {e}")
