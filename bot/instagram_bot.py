from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
# from undetected_chromedriver import Chrome as UndetectedChrome # Option for stealth
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException

from .utils import get_logger, get_config, get_selector, take_screenshot
from .anti_detection import human_delay, get_random_user_agent, type_like_human, apply_browser_fingerprint_tweaks
from .session_manager import SessionManager

class InstagramBot:
    def __init__(self, username, password_is_prompted=False): # password can be prompted
        self.config = get_config()
        self.logger = get_logger()
        self.username = username
        self._password_is_prompted = password_is_prompted # If true, password was obtained via getpass
        
        self.base_url = self.config.get('GeneralSettings', 'base_url', fallback="https://www.instagram.com")
        self.implicit_wait = self.config.getint('GeneralSettings', 'implicitly_wait_time', fallback=10)
        self.page_load_timeout = self.config.getint('GeneralSettings', 'page_load_timeout', fallback=30)
        self.script_timeout = self.config.getint('GeneralSettings', 'script_timeout', fallback=30)
        self.max_retries = self.config.getint('GeneralSettings', 'max_retries_on_error', fallback=2)

        self.session_manager = SessionManager(self.username)
        self.driver = None
        self.wait = None
        self._is_pro = False # Will be set by license check

    def set_pro_status(self, is_pro):
        self._is_pro = is_pro
        if self._is_pro:
            self.logger.info("PRO features enabled for this session.")

    def _setup_driver_options(self):
        options = webdriver.ChromeOptions()
        if self.config.getboolean('GeneralSettings', 'headless_browser', fallback=True):
            options.add_argument("--headless=new") # Updated headless argument

        if self.config.getboolean('AntiDetection', 'use_random_user_agent', fallback=True):
            ua = get_random_user_agent()
            if ua:
                options.add_argument(f"user-agent={ua}")
                self.logger.info(f"Using User-Agent: {ua}")
        
        apply_browser_fingerprint_tweaks(options) # From anti_detection.py

        if self._is_pro:
            proxy_host = self.config.get('ProSettings', 'proxy_host', fallback=None)
            if proxy_host:
                proxy_type = self.config.get('ProSettings', 'proxy_type', fallback='http')
                proxy_port = self.config.get('ProSettings', 'proxy_port', fallback=None)
                proxy_user = self.config.get('ProSettings', 'proxy_user', fallback=None)
                proxy_pass = self.config.get('ProSettings', 'proxy_pass', fallback=None)
                
                proxy_str = f"{proxy_type}://"
                if proxy_user and proxy_pass:
                    proxy_str += f"{proxy_user}:{proxy_pass}@"
                proxy_str += f"{proxy_host}:{proxy_port if proxy_port else ''}"
                
                options.add_argument(f'--proxy-server={proxy_str}')
                self.logger.info(f"Using PROXY: {proxy_host} (type: {proxy_type})")
        
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
        options.add_experimental_option("prefs", prefs)
        return options

    def initialize_driver(self):
        try:
            options = self._setup_driver_options()
            # For standard ChromeDriver:
            self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            # For UndetectedChromeDriver (install it and uncomment):
            # import undetected_chromedriver as uc
            # self.driver = uc.Chrome(options=options, version_main=110) # Match your Chrome version
            
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.set_script_timeout(self.script_timeout)
            # self.driver.implicitly_wait(self.implicit_wait) # Use explicit waits more often
            self.wait = WebDriverWait(self.driver, self.implicit_wait)
            self.logger.info("WebDriver initialized successfully.")
            return True
        except Exception as e:
            self.logger.critical(f"Fatal error initializing WebDriver: {e}. Check Chrome/ChromeDriver installation and version compatibility.")
            return False

    def _find_element(self, selector_key, timeout=None, parent_element=None):
        sel_type, sel_val = get_selector(selector_key)
        if not sel_type or not sel_val:
            self.logger.error(f"Selector for '{selector_key}' not found or invalid.")
            return None
        
        search_context = parent_element if parent_element else self.driver
        current_wait_time = timeout if timeout is not None else self.implicit_wait
        
        for attempt in range(self.max_retries + 1):
            try:
                element = WebDriverWait(search_context, current_wait_time).until(
                    EC.presence_of_element_located((sel_type, sel_val))
                )
                # Optional: check for visibility
                # element = WebDriverWait(search_context, current_wait_time).until(
                #     EC.visibility_of_element_located((sel_type, sel_val))
                # )
                return element
            except TimeoutException:
                if attempt == self.max_retries:
                    self.logger.warning(f"Element '{selector_key}' ({sel_val}) not found after {self.max_retries+1} attempts (timeout: {current_wait_time}s).")
                    return None
                self.logger.debug(f"Element '{selector_key}' not found, attempt {attempt+1}, retrying...")
                human_delay("navigation") # Small delay before retry
            except StaleElementReferenceException: # If element becomes stale during retries
                 if attempt == self.max_retries:
                    self.logger.warning(f"Element '{selector_key}' became stale and not found after retries.")
                    return None
                 self.logger.debug(f"Element '{selector_key}' stale, attempt {attempt+1}, retrying search context...")
                 search_context = parent_element if parent_element else self.driver # Re-evaluate search context

        return None # Should be unreachable if max_retries is handled right

    def _find_elements(self, selector_key, timeout=None, parent_element=None):
        # Similar logic to _find_element but for multiple elements
        sel_type, sel_val = get_selector(selector_key)
        if not sel_type or not sel_val: return []
        search_context = parent_element if parent_element else self.driver
        current_wait_time = timeout if timeout is not None else self.implicit_wait
        try:
            return WebDriverWait(search_context, current_wait_time).until(
                EC.presence_of_all_elements_located((sel_type, sel_val))
            )
        except TimeoutException:
            self.logger.debug(f"Elements '{selector_key}' ({sel_val}) not found (timeout: {current_wait_time}s).")
            return []

    def _click_element(self, element_or_selector_key, description="element", timeout=None, scroll_into_view=True):
        if isinstance(element_or_selector_key, str): # It's a selector key
            element = self._find_element(element_or_selector_key, timeout=timeout)
        else: # It's already a WebElement
            element = element_or_selector_key

        if not element:
            self.logger.warning(f"Cannot click: {description} (selector: {element_or_selector_key if isinstance(element_or_selector_key, str) else 'WebElement'}) not found.")
            return False

        for attempt in range(self.max_retries + 1):
            try:
                if scroll_into_view:
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    human_delay("navigation") # Wait for scroll
                
                # Wait for element to be clickable
                clickable_element = self.wait.until(EC.element_to_be_clickable(element))
                clickable_element.click()
                self.logger.info(f"Clicked {description}.")
                human_delay("default")
                return True
            except ElementClickInterceptedException:
                self.logger.warning(f"Click intercepted for {description} (attempt {attempt+1}). Trying JS click.")
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    self.logger.info(f"Clicked {description} using JavaScript fallback.")
                    human_delay("default")
                    return True
                except Exception as e_js:
                    if attempt == self.max_retries:
                        self.logger.error(f"JS click also failed for {description}: {e_js}")
                        take_screenshot(self.driver, f"click_intercept_fail_{description.replace(' ','_')}")
                        return False
            except StaleElementReferenceException:
                self.logger.warning(f"Element {description} became stale during click (attempt {attempt+1}). Refinding...")
                if isinstance(element_or_selector_key, str): # Re-find if it was a key
                    element = self._find_element(element_or_selector_key, timeout=timeout) # Re-find
                    if not element: return False # If cannot re-find, fail
                else: # If it was a WebElement, we can't easily re-find without original selector
                    if attempt == self.max_retries:
                        self.logger.error(f"Stale element {description} could not be re-clicked.")
                        return False
            except Exception as e:
                if attempt == self.max_retries:
                    self.logger.error(f"Unexpected error clicking {description}: {e}")
                    take_screenshot(self.driver, f"click_error_{description.replace(' ','_')}")
                    return False
            
            self.logger.debug(f"Retrying click for {description} (attempt {attempt+1})...")
            human_delay("navigation") # Delay before retry
        return False


    def _is_logged_in(self):
        # Check for a reliable element on the home page
        home_indicator = self._find_element("home_page.home_icon_indicator", timeout=5)
        if home_indicator:
            self.logger.debug("User appears to be logged in (home indicator found).")
            return True
        self.logger.debug("User does not appear to be logged in (home indicator not found).")
        return False

    def login(self):
        if not self.driver:
            self.logger.error("Driver not initialized. Cannot login.")
            return False

        self.driver.get(self.base_url + "/") # Go to main page
        human_delay("navigation")

        if self.session_manager.load_cookies(self.driver):
            self.driver.refresh() # Refresh to apply cookies and check session
            human_delay("navigation")
            if self._is_logged_in():
                self.logger.info(f"Successfully logged in as {self.username} using saved session.")
                return True
            else:
                self.logger.info("Saved session invalid or expired. Proceeding with manual login.")
        
        self.driver.get(self.base_url + "/accounts/login/")
        human_delay("navigation")

        try:
            # Username
            username_field = self._find_element("login_page.username_field", timeout=10)
            if not username_field:
                self.logger.error("Username field not found on login page.")
                take_screenshot(self.driver, "login_username_field_fail")
                return False
            type_like_human(username_field, self.username)

            # Password
            password_field = self._find_element("login_page.password_field")
            if not password_field:
                self.logger.error("Password field not found on login page.")
                take_screenshot(self.driver, "login_password_field_fail")
                return False
            
            # Get password (prompt if needed, or from config)
            password_to_use = ""
            if self._password_is_prompted: # If main.py prompted it
                # Assume password was passed to main and is now an instance var if needed, or re-prompt here
                # For simplicity, assume if prompted, it was handled before bot init
                # This part needs careful design based on how you handle getpass in main.py
                # Let's assume it's passed via constructor if prompted externally.
                # If not prompted, get from config (which is bad practice for passwords)
                 pass # Password should be set if prompted
            else:
                password_to_use = self.config.get('Credentials', 'password', fallback="")

            if not password_to_use: # If still no password (e.g. not prompted and not in config)
                import getpass
                self.logger.info("Password not found in config and was not prompted by main script.")
                password_to_use = getpass.getpass(f"Enter password for {self.username}: ")

            type_like_human(password_field, password_to_use)
            password_to_use = "" # Clear from memory

            # Login Button
            if not self._click_element("login_page.login_button", "Login button"):
                self.logger.error("Failed to click login button or button not found.")
                take_screenshot(self.driver, "login_button_click_fail")
                # Check for login error messages here (e.g., "Sorry, your password was incorrect.")
                return False

            human_delay("navigation") # Wait for login process

            # Handle "Save Info" and "Turn on Notifications" popups
            self._click_element("login_page.save_info_not_now_button", "'Not Now' (Save Info)", timeout=7, scroll_into_view=False)
            human_delay("default")
            self._click_element("login_page.turn_on_notifications_not_now_button", "'Not Now' (Notifications)", timeout=7, scroll_into_view=False)
            human_delay("default")
            
            if self._is_logged_in():
                self.logger.info(f"Manual login successful for {self.username}.")
                self.session_manager.save_cookies(self.driver)
                return True
            else:
                self.logger.error("Login failed after submitting credentials. Check for error messages on page.")
                take_screenshot(self.driver, "login_failed_after_submit")
                # Check for specific error messages (e.g., wrong password, suspicious login attempt)
                return False

        except Exception as e:
            self.logger.error(f"An unexpected error occurred during login: {e}", exc_info=True)
            take_screenshot(self.driver, "login_unexpected_error")
            return False

    def navigate_to_url(self, url_suffix):
        full_url = self.base_url + url_suffix
        self.logger.info(f"Navigating to: {full_url}")
        try:
            self.driver.get(full_url)
            human_delay("navigation")
            # Add a check to see if page loaded correctly (e.g. specific element or title)
            return True
        except TimeoutException:
            self.logger.error(f"Timeout loading URL: {full_url}")
            take_screenshot(self.driver, f"nav_timeout_{url_suffix.replace('/','_')}")
            return False
        except Exception as e:
            self.logger.error(f"Error navigating to {full_url}: {e}")
            return False

    def like_post_in_modal(self):
        """Assumes a post modal (popup after clicking thumbnail) is open."""
        # Check if already liked
        if self._find_element("post_interaction.modal_like_button_liked", timeout=2):
            self.logger.info("Post in modal is already liked.")
            return False # Or True, depending on if "already liked" is a success

        if self._click_element("post_interaction.modal_like_button_unliked", "Like button in modal"):
            self.logger.info("Liked post in modal.")
            return True
        else:
            self.logger.warning("Failed to like post in modal.")
            return False

    def close_post_modal(self):
        return self._click_element("post_interaction.modal_close_button", "Post modal close button")

    def view_story_from_ring(self, story_ring_element):
        if not self._click_element(story_ring_element, "Story ring"):
            return False
        
        self.logger.info("Viewing story...")
        human_delay("story_view") # Configurable delay for "watching"

        # You might want to click "next" a few times if the story has multiple segments
        # next_button = self._find_element("story_viewer.story_next_button", timeout=3)
        # if next_button: self._click_element(next_button, "Story Next")

        if self._click_element("story_viewer.story_close_button", "Story close button", timeout=5):
            self.logger.info("Story viewed and closed.")
            return True
        else: # Fallback if close button not found
            self.logger.warning("Story close button not found. Attempting to press Escape.")
            from selenium.webdriver.common.keys import Keys
            try:
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                human_delay("default")
                return True
            except: return False


    def check_for_action_block(self):
        """ Checks for common action block popups. """
        blocked_element = self._find_element("error_popups.action_blocked_text", timeout=3)
        if blocked_element and blocked_element.is_displayed():
            self.logger.critical(f"ACTION BLOCKED DETECTED for {self.username}!")
            take_screenshot(self.driver, "action_block_detected")
            # Here you would trigger logic to pause this account for a long time
            # and potentially notify the user.
            # For now, try to close the popup if possible.
            # You might need a selector for the "OK" or "Close" button on the block popup.
            return True
        return False

    def quit_driver(self):
        if self.driver:
            try:
                self.logger.info("Quitting WebDriver.")
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error quitting WebDriver: {e}")
            finally:
                self.driver = None
