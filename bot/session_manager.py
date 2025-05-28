import os
import pickle
import shutil # For removing corrupted cookie files safely
from .utils import get_logger, get_config # Use . for relative import
from .anti_detection import human_delay # Use . for relative import

class SessionManager:
    def __init__(self, username):
        self.username = username
        self.logger = get_logger()
        self.config = get_config()
        if not self.config:
            self.logger.critical("SessionManager: Config not loaded. Cannot determine cookies path.")
            # Handle this critical failure, perhaps by raising an exception
            # For now, try a default path but log error
            cookies_base_rel_path = ".cookies/"
        else:
            cookies_base_rel_path = self.config.get('SessionManagement', 'cookies_path', fallback='.cookies/')

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cookies_base_abs_path = os.path.join(project_root, cookies_base_rel_path)

        if not os.path.exists(self.cookies_base_abs_path):
            try:
                os.makedirs(self.cookies_base_abs_path)
            except OSError as e:
                self.logger.error(f"Could not create cookies directory {self.cookies_base_abs_path}: {e}")
                # Fallback or raise error if critical
        
        self.cookie_file_path = os.path.join(self.cookies_base_abs_path, f"{self.username}_cookies.pkl")
        
        # self.encrypt_cookies = self.config.getboolean('SessionManagement', 'encrypt_cookies', fallback=False)
        # if self.encrypt_cookies: # Placeholder for encryption logic
        #     self.logger.info("Cookie encryption logic (placeholder) would be active.")

    def save_cookies(self, driver):
        if not driver:
            self.logger.warning("Attempted to save cookies, but driver is None.")
            return
        try:
            cookies = driver.get_cookies()
            if not cookies:
                self.logger.info(f"No cookies to save for {self.username}.")
                return

            with open(self.cookie_file_path, 'wb') as f:
                pickle.dump(cookies, f)
            self.logger.info(f"Session cookies saved for {self.username} to {self.cookie_file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save cookies for {self.username} to {self.cookie_file_path}: {e}")

    def load_cookies(self, driver):
        if not driver:
            self.logger.warning("Attempted to load cookies, but driver is None.")
            return False
            
        if not os.path.exists(self.cookie_file_path):
            self.logger.info(f"No cookie file found for {self.username} at {self.cookie_file_path}")
            return False
        try:
            with open(self.cookie_file_path, 'rb') as f:
                cookies = pickle.load(f)
            
            if not cookies:
                self.logger.info(f"Cookie file for {self.username} is empty.")
                return False

            # Instagram might require being on the correct domain before adding cookies.
            base_url = self.config.get('GeneralSettings', 'base_url', fallback="https://www.instagram.com")
            current_domain_is_instagram = False
            try:
                current_domain_is_instagram = ".instagram.com" in driver.current_url
            except Exception: # Handle cases where driver.current_url might fail (e.g. about:blank)
                pass

            if not current_domain_is_instagram:
                self.logger.debug(f"Not on Instagram domain (current: {driver.current_url}). Navigating to base URL before loading cookies.")
                driver.get(base_url + "/")
                human_delay("navigation")

            for cookie in cookies:
                # Selenium sometimes has issues with 'expiry' float vs int, ensure it's int if present
                if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                    cookie['expiry'] = int(cookie['expiry'])
                
                # Some cookies might not have a domain set, or it might be too broad.
                # It's generally safer to let Selenium handle this or ensure they are for '.instagram.com'
                # if 'domain' not in cookie or not cookie['domain'].endswith('.instagram.com'):
                #     cookie['domain'] = '.instagram.com' # Or skip if domain is wrong

                try:
                    driver.add_cookie(cookie)
                except Exception as e_add: # Catch specific cookie errors if known
                    self.logger.debug(f"Could not add cookie '{cookie.get('name', 'N/A')}': {e_add}. Skipping.")
            
            self.logger.info(f"Loaded {len(cookies)} cookies for {self.username} from {self.cookie_file_path}.")
            return True
        except pickle.UnpicklingError as e_pickle:
            self.logger.error(f"Error unpickling cookie file for {self.username} (corrupted?): {e_pickle}")
            self._handle_corrupted_cookie_file()
            return False
        except Exception as e:
            self.logger.error(f"Failed to load cookies for {self.username} from {self.cookie_file_path}: {e}")
            self._handle_corrupted_cookie_file() # Assume corruption on generic error too
            return False

    def _handle_corrupted_cookie_file(self):
        self.logger.warning(f"Attempting to remove potentially corrupted cookie file: {self.cookie_file_path}")
        try:
            if os.path.exists(self.cookie_file_path):
                shutil.move(self.cookie_file_path, self.cookie_file_path + ".corrupted") # Rename instead of direct delete
                self.logger.info(f"Renamed corrupted cookie file to {self.cookie_file_path}.corrupted")
        except OSError as e_os:
            self.logger.error(f"Could not remove/rename corrupted cookie file {self.cookie_file_path}: {e_os}")

    def clear_cookies_file(self):
        """Deletes the cookie file for the current user."""
        if os.path.exists(self.cookie_file_path):
            try:
                os.remove(self.cookie_file_path)
                self.logger.info(f"Cleared cookie file for {self.username} from {self.cookie_file_path}")
            except OSError as e:
                self.logger.error(f"Failed to clear cookie file for {self.username}: {e}")
        else:
            self.logger.info(f"No cookie file to clear for {self.username} at {self.cookie_file_path}")
