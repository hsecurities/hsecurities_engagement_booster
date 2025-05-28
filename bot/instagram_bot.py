from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
# from undetected_chromedriver import Chrome as UndetectedChrome # Option for stealth
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from selenium.webdriver.common.keys import Keys # For pressing Escape, etc.

from .utils import get_logger, get_config, get_selector, take_screenshot # Relative imports
from .anti_detection import human_delay, get_random_user_agent, type_like_human, apply_browser_fingerprint_tweaks # Relative
from .session_manager import SessionManager # Relative

class InstagramBot:
    def __init__(self, username, password_was_prompted=False, external_password=None):
        self.config = get_config() # Ensured to be loaded by main or utils
        self.logger = get_logger() # Ensured to be initialized
        
        if not self.config:
            self.logger.critical("InstagramBot: Critical - Configuration not loaded. Aborting initialization.")
            raise ValueError("Configuration is not loaded. Cannot initialize InstagramBot.")

        self.username = username
        self._password_was_prompted = password_was_prompted
        self._external_password = external_password # Store password if passed from prompt
        
        self.base_url = self.config.get('GeneralSettings', 'base_url', fallback="https://www.instagram.com")
        self.implicit_wait_timeout = self.config.getint('GeneralSettings', 'implicitly_wait_time', fallback=10)
        self.page_load_timeout = self.config.getint('GeneralSettings', 'page_load_timeout', fallback=45)
        self.script_timeout = self.config.getint('GeneralSettings', 'script_timeout', fallback=30)
        self.max_retries_on_error = self.config.getint('GeneralSettings', 'max_retries_on_error', fallback=2)

        self.session_manager = SessionManager(self.username)
        self.driver = None
        self.wait = None # WebDriverWait instance
        self._is_pro_user = False # Default, can be set by main script after license check

    def set_pro_status(self, is_pro):
        self._is_pro_user = is_pro
        if self._is_pro_user:
            self.logger.info("Pro user status set: Proxy and other Pro features may be enabled based on config.")

    def _setup_driver_options(self):
        options = webdriver.ChromeOptions()
        if self.config.getboolean('GeneralSettings', 'headless_browser', fallback=True):
            options.add_argument("--headless=new") # Recommended new headless mode
            self.logger.info("Headless mode enabled.")
        else:
            self.logger.info("Headless mode disabled (browser window will be visible).")


        if self.config.getboolean('AntiDetection', 'use_random_user_agent', fallback=True):
            ua = get_random_user_agent()
            if ua:
                options.add_argument(f"user-agent={ua}")
                self.logger.info(f"Using User-Agent: {ua}")
            else:
                self.logger.warning("Failed to get random user agent; WebDriver will use its default.")
        
        apply_browser_fingerprint_tweaks(options) # From anti_detection.py

        if self._is_pro_user: # Check Pro status for proxy
            proxy_host = self.config.get('ProSettings', 'proxy_host', fallback=None)
            if proxy_host and proxy_host.strip(): # Ensure host is not empty
                proxy_type = self.config.get('ProSettings', 'proxy_type', fallback='http').lower()
                proxy_port = self.config.get('ProSettings', 'proxy_port', fallback=None)
                proxy_user = self.config.get('ProSettings', 'proxy_user', fallback=None)
                proxy_pass = self.config.get('ProSettings', 'proxy_pass', fallback=None)
                
                if not proxy_port:
                    self.logger.warning(f"Proxy host '{proxy_host}' provided for Pro user, but no port. Proxy will not be used.")
                else:
                    proxy_str_config = f"{proxy_type}://"
                    if proxy_user and proxy_user.strip() and proxy_pass: # Password can be empty string
                        proxy_str_config += f"{proxy_user}:{proxy_pass}@"
                    proxy_str_config += f"{proxy_host}:{proxy_port}"
                    
                    options.add_argument(f'--proxy-server={proxy_str_config}')
                    self.logger.info(f"PRO: Using proxy: {proxy_type}://{proxy_host}:{proxy_port}")
            elif self._is_pro_user:
                 self.logger.info("PRO user, but no proxy host configured in ProSettings.")
        
        # Common options
        options.add_argument("--disable-gpu") # Often recommended for headless
        options.add_argument("--no-sandbox") # Required for some environments (e.g. Docker)
        options.add_argument("--disable-dev-shm-usage") # Overcomes limited resource problems
        options.add_argument("--log-level=3") # Suppress non-critical browser console logs
        options.add_experimental_option('excludeSwitches', ['enable-logging']) # Further suppress console noise
        return options

    def initialize_driver(self):
        self.logger.info("Initializing WebDriver...")
        try:
            options = self._setup_driver_options()
            
            # Standard ChromeDriver via webdriver-manager
            self.logger.debug("Attempting to install/use ChromeDriver via webdriver-manager...")
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Optional: If you want to use UndetectedChromeDriver
            # (ensure it's installed: pip install undetected-chromedriver)
            # import undetected_chromedriver as uc
            # self.logger.debug("Attempting to use UndetectedChromeDriver...")
            # # You might need to specify chromedriver version if auto-detection fails
            # # chrome_major_version = 114 # Example, get your actual Chrome major version
            # self.driver = uc.Chrome(options=options) #, version_main=chrome_major_version)
            
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.set_script_timeout(self.script_timeout)
            # self.driver.implicitly_wait(self.implicit_wait_timeout) # Use explicit waits more often
            self.wait = WebDriverWait(self.driver, self.implicit_wait_timeout) # Default wait for explicit conditions
            self.logger.info("WebDriver initialized successfully.")
            return True
        except WebDriverException as wde:
            if "cannot find chrome binary" in str(wde).lower():
                self.logger.critical("CRITICAL: Chrome browser binary not found. Please ensure Google Chrome is installed correctly and in PATH.")
            elif "this version of chromedriver only supports chrome version" in str(wde).lower():
                 self.logger.critical(f"CRITICAL: ChromeDriver/Chrome version mismatch. Error: {wde}")
                 self.logger.critical("Try deleting existing ChromeDriver (if webdriver-manager cached an old one) or update Chrome.")
            else:
                self.logger.critical(f"Fatal WebDriverException during initialization: {wde}")
            return False
        except Exception as e:
            self.logger.critical(f"Fatal generic error initializing WebDriver: {e}", exc_info=True)
            return False

    def _get_element_explicitly(self, by_type, selector_value, timeout_seconds, context=None, visible=False):
        """Helper for explicit waits."""
        search_context = context if context else self.driver
        wait_condition = EC.visibility_of_element_located if visible else EC.presence_of_element_located
        try:
            return WebDriverWait(search_context, timeout_seconds).until(
                wait_condition((by_type, selector_value))
            )
        except TimeoutException:
            return None


    def _find_element(self, selector_key, timeout_override=None, parent_element=None, visible=False):
        sel_type, sel_val = get_selector(selector_key) # From utils
        if not sel_type or not sel_val:
            self.logger.error(f"Selector for '{selector_key}' is invalid or not found in selectors.yaml.")
            return None
        
        current_timeout = timeout_override if timeout_override is not None else self.implicit_wait_timeout
        
        for attempt in range(self.max_retries_on_error + 1):
            try:
                element = self._get_element_explicitly(sel_type, sel_val, current_timeout, context=parent_element, visible=visible)
                if element:
                    return element
                else: # TimeoutException was handled by _get_element_explicitly returning None
                    if attempt == self.max_retries_on_error:
                        self.logger.warning(f"Element '{selector_key}' ({sel_val}) not found after {self.max_retries_on_error+1} attempts (timeout: {current_timeout}s).")
                        return None
                    self.logger.debug(f"Element '{selector_key}' not found, attempt {attempt+1}, retrying...")
                    human_delay("navigation", min_override=0.5 + attempt, max_override=1.5 + attempt) # Small delay before retry
            except StaleElementReferenceException:
                 if attempt == self.max_retries_on_error:
                    self.logger.warning(f"Element '{selector_key}' ({sel_val}) became stale and not found after retries.")
                    return None
                 self.logger.debug(f"Element '{selector_key}' stale, attempt {attempt+1}, retrying find...")
        return None

    def _find_elements(self, selector_key, timeout_override=None, parent_element=None):
        sel_type, sel_val = get_selector(selector_key)
        if not sel_type or not sel_val:
            self.logger.error(f"Selector for list '{selector_key}' is invalid or not found.")
            return []
        
        search_context = parent_element if parent_element else self.driver
        current_timeout = timeout_override if timeout_override is not None else self.implicit_wait_timeout
        try:
            return WebDriverWait(search_context, current_timeout).until(
                EC.presence_of_all_elements_located((sel_type, sel_val))
            )
        except TimeoutException:
            self.logger.debug(f"Elements for '{selector_key}' ({sel_val}) not found (timeout: {current_timeout}s).")
            return []

    def _click_element(self, element_or_selector_key, description="element", timeout_override=None, scroll_into_view=True, allow_js_fallback=True):
        if isinstance(element_or_selector_key, str):
            # Find element, ensuring it's visible and clickable might be better here
            element = self._find_element(element_or_selector_key, timeout_override=timeout_override, visible=True)
        else:
            element = element_or_selector_key # Assumed it's a WebElement

        if not element:
            self.logger.warning(f"Cannot click: {description} (target: '{element_or_selector_key if isinstance(element_or_selector_key, str) else 'WebElement'}') not found or not visible.")
            return False

        for attempt in range(self.max_retries_on_error + 1):
            try:
                if scroll_into_view:
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center', inline: 'center'});", element)
                    human_delay("navigation", min_override=0.3, max_override=0.8) # Wait for scroll to settle

                # Explicitly wait for element to be clickable
                wait_time_clickable = timeout_override if timeout_override is not None else self.implicit_wait_timeout / 2 # Shorter for clickable check
                clickable_element = WebDriverWait(self.driver, max(1, wait_time_clickable)).until(EC.element_to_be_clickable(element))
                
                clickable_element.click()
                self.logger.info(f"Clicked {description}.")
                human_delay("default") # Standard delay after a successful action
                return True
            except ElementClickInterceptedException as eci:
                self.logger.warning(f"Click intercepted for {description} (attempt {attempt+1}): {str(eci).splitlines()[0]}.")
                if allow_js_fallback:
                    self.logger.info("Attempting JavaScript click as fallback...")
                    try:
                        self.driver.execute_script("arguments[0].click();", element)
                        self.logger.info(f"Clicked {description} using JavaScript fallback.")
                        human_delay("default")
                        return True
                    except Exception as e_js:
                        self.logger.error(f"JavaScript click also failed for {description}: {e_js}")
                        # No retry after JS fail for this attempt, will retry standard click if attempts remain
                if attempt == self.max_retries_on_error:
                    take_screenshot(self.driver, f"final_click_intercept_{description.replace(' ','_')}")
                    return False
            except StaleElementReferenceException:
                self.logger.warning(f"Element {description} became stale during click (attempt {attempt+1}).")
                if isinstance(element_or_selector_key, str): # Re-find if it was a key
                    element = self._find_element(element_or_selector_key, timeout_override=timeout_override, visible=True)
                    if not element:
                        self.logger.error(f"Could not re-find stale element {description}.")
                        return False # If cannot re-find, fail
                    self.logger.debug("Re-found stale element, retrying click.")
                else: # If it was a WebElement, we can't easily re-find
                    if attempt == self.max_retries_on_error:
                        self.logger.error(f"Stale WebElement {description} could not be re-clicked without original selector.")
                        return False
            except TimeoutException as te: # e.g. from element_to_be_clickable
                self.logger.warning(f"Timeout waiting for {description} to be clickable (attempt {attempt+1}): {str(te).splitlines()[0]}")
                if attempt == self.max_retries_on_error:
                    take_screenshot(self.driver, f"timeout_clickable_{description.replace(' ','_')}")
                    return False
            except Exception as e:
                self.logger.error(f"Unexpected error clicking {description} (attempt {attempt+1}): {e}", exc_info=True)
                if attempt == self.max_retries_on_error:
                    take_screenshot(self.driver, f"unexpected_click_error_{description.replace(' ','_')}")
                    return False
            
            self.logger.debug(f"Retrying click for {description} (attempt {attempt+1} of {self.max_retries_on_error})...")
            human_delay("navigation", min_override=0.5 + attempt, max_override=1.5 + attempt) # Delay before retry
        return False


    def _is_logged_in(self):
        # Check for a reliable element on the home page, or lack of login page elements
        self.logger.debug("Checking login status...")
        # Prioritize checking for a positive login indicator
        home_indicator = self._find_element("home_page.home_icon_indicator", timeout_override=3) # Quick check
        if home_indicator:
            self.logger.info("User is logged in (home indicator found).")
            return True
        
        # If no home icon, check if we are on the login page
        login_username_field = self._find_element("login_page.username_field", timeout_override=2)
        if login_username_field:
            self.logger.info("User is not logged in (login page elements found).")
            return False
            
        self.logger.warning("Login status unclear: No definitive home indicator or login page elements found. Assuming not logged in for safety.")
        # Potentially take a screenshot here if status is ambiguous after a login attempt
        return False

    def login(self):
        if not self.driver:
            self.logger.critical("Driver not initialized. Cannot login.")
            return False

        self.logger.info(f"Attempting login for user: {self.username}")
        self.driver.get(self.base_url + "/") # Go to main page, not directly to login
        human_delay("navigation")

        if self.session_manager.load_cookies(self.driver):
            self.logger.info("Cookies loaded. Refreshing page to validate session...")
            self.driver.refresh()
            human_delay("navigation")
            if self._is_logged_in():
                self.logger.info(f"Successfully logged in as {self.username} using saved session.")
                return True
            else:
                self.logger.info("Saved session invalid, expired, or login status unclear. Proceeding with manual login.")
                # Optionally clear cookies if they led to an unclear state
                # self.session_manager.clear_cookies_file()
        
        # Navigate to login page if not already there or if cookie login failed
        if "/accounts/login/" not in self.driver.current_url:
            self.driver.get(self.base_url + "/accounts/login/")
            human_delay("navigation")

        try:
            username_field = self._find_element("login_page.username_field", timeout_override=10, visible=True)
            if not username_field:
                self.logger.error("Username input field not found on login page.")
                take_screenshot(self.driver, "login_fail_no_user_field")
                return False
            type_like_human(username_field, self.username)

            password_field = self._find_element("login_page.password_field", visible=True)
            if not password_field:
                self.logger.error("Password input field not found on login page.")
                take_screenshot(self.driver, "login_fail_no_pass_field")
                return False
            
            current_password = ""
            if self._external_password: # Password was passed from main via getpass
                current_password = self._external_password
                self._external_password = "" # Clear after use
            elif not self._password_was_prompted: # Not prompted by main, try config (less secure)
                current_password = self.config.get('Credentials', 'password', fallback="")
            
            if not current_password: # Still no password, prompt now if allowed (should have been handled by main ideally)
                 import getpass
                 self.logger.info("Password not available. Prompting now...")
                 current_password = getpass.getpass(f"Enter Instagram password for {self.username}: ")

            if not current_password:
                self.logger.error("Password not provided. Cannot login.")
                return False

            type_like_human(password_field, current_password)
            current_password = "" # Clear from memory immediately

            if not self._click_element("login_page.login_button", "Login button"):
                self.logger.error("Failed to click the Login button or button not found.")
                take_screenshot(self.driver, "login_fail_no_login_button")
                # Check for specific error messages on page like "incorrect password"
                return False

            human_delay("navigation", min_override=3, max_override=6) # Longer delay for login processing

            # Handle "Save Info" and "Turn on Notifications" popups. Timeout is short as they may not appear.
            self._click_element("login_page.save_info_not_now_button", "'Not Now' (Save Info)", timeout_override=7, scroll_into_view=False)
            # No significant delay needed if it's just clicking "Not Now"
            self._click_element("login_page.turn_on_notifications_not_now_button", "'Not Now' (Notifications)", timeout_override=7, scroll_into_view=False)
            
            if self._is_logged_in():
                self.logger.info(f"Manual login successful for {self.username}.")
                self.session_manager.save_cookies(self.driver)
                return True
            else:
                self.logger.error("Login failed after submitting credentials or login status unclear.")
                take_screenshot(self.driver, "login_fail_after_submit")
                # Check for specific error messages (e.g., wrong password, suspicious login attempt, challenge)
                if self.check_for_challenge_or_block("login_fail_after_submit"): # Pass context for screenshot name
                    # Further handling for challenges would go here
                    pass
                return False

        except Exception as e:
            self.logger.critical(f"An unexpected critical error occurred during login process: {e}", exc_info=True)
            take_screenshot(self.driver, "login_critical_error")
            return False

    def navigate_to_url(self, url_suffix_or_full_url):
        if url_suffix_or_full_url.startswith("http"):
            target_url = url_suffix_or_full_url
        else:
            target_url = self.base_url + url_suffix_or_full_url
        
        self.logger.info(f"Navigating to: {target_url}")
        try:
            self.driver.get(target_url)
            human_delay("navigation")
            # TODO: Add a check here to ensure page loaded correctly if possible (e.g., wait for a known element)
            # For example, for a hashtag page, wait for "hashtag_page.recent_posts_section_header"
            return True
        except TimeoutException:
            self.logger.error(f"Timeout loading URL: {target_url}")
            take_screenshot(self.driver, f"nav_timeout_{target_url.split('/')[-1][:20]}") # Sanitize for filename
            return False
        except Exception as e:
            self.logger.error(f"Generic error navigating to {target_url}: {e}", exc_info=True)
            take_screenshot(self.driver, f"nav_error_{target_url.split('/')[-1][:20]}")
            return False

    def like_post_in_modal(self):
        self.logger.debug("Attempting to like post in modal...")
        # Ensure modal is present first (optional, but good for context)
        modal_dialog = self._find_element("post_interaction.modal_dialog", timeout_override=3)
        if not modal_dialog:
            self.logger.warning("Post modal dialog not found. Cannot attempt like.")
            return False

        # Check if already liked by looking for the "Unlike" button state
        # Note: Selectors for liked/unliked state must be distinct and accurate
        if self._find_element("post_interaction.modal_like_button_liked", timeout_override=1, parent_element=modal_dialog):
            self.logger.info("Post in modal is already liked.")
            return True # Or False if "already liked" isn't a success for your logic

        if self._click_element("post_interaction.modal_like_button_unliked", "Like button in modal", parent_element=modal_dialog):
            self.logger.info("Successfully liked post in modal.")
            return True
        else:
            self.logger.warning("Failed to click like button in modal (may not be present or interactable).")
            take_screenshot(self.driver, "like_in_modal_fail")
            return False

    def close_post_modal(self):
        self.logger.debug("Attempting to close post modal...")
        if self._click_element("post_interaction.modal_close_button", "Post modal close button"):
            self.logger.info("Post modal closed.")
            return True
        else: # Fallback if dedicated close button fails
            self.logger.warning("Standard post modal close button failed. Attempting Escape key.")
            try:
                # Find a high-level element to send keys to, or body
                body_el = self.driver.find_element(By.TAG_NAME, "body")
                body_el.send_keys(Keys.ESCAPE)
                human_delay("default")
                self.logger.info("Pressed Escape key to close modal.")
                # Verify modal is actually closed (e.g. modal_dialog is no longer present)
                if not self._find_element("post_interaction.modal_dialog", timeout_override=2):
                    return True
            except Exception as e_esc:
                self.logger.error(f"Error pressing Escape key: {e_esc}")
            take_screenshot(self.driver, "close_modal_fail")
            return False

    def view_story_from_ring(self, story_ring_element, story_owner_username="UnknownUser"):
        self.logger.info(f"Attempting to view story for {story_owner_username}...")
        if not self._click_element(story_ring_element, f"Story ring for {story_owner_username}"):
            self.logger.warning(f"Failed to click story ring for {story_owner_username}.")
            return False
        
        self.logger.info(f"Viewing story of {story_owner_username}...")
        # Simulate watching for a configured duration
        human_delay("story_view") 
        
        # Optional: Click "Next" a few times if the story has multiple segments
        # You'd need a loop and check for "story_viewer.story_next_button"
        # Be careful not to get stuck if the last segment is reached.

        if self._click_element("story_viewer.story_close_button", "Story close button", timeout_override=5):
            self.logger.info(f"Story of {story_owner_username} viewed and closed.")
            return True
        else: # Fallback
            self.logger.warning("Standard story close button failed. Attempting Escape key.")
            try:
                body_el = self.driver.find_element(By.TAG_NAME, "body")
                body_el.send_keys(Keys.ESCAPE)
                human_delay("default")
                self.logger.info("Pressed Escape key to close story viewer.")
                return True # Assume it worked
            except Exception as e_esc_story:
                self.logger.error(f"Error pressing Escape for story viewer: {e_esc_story}")
            take_screenshot(self.driver, f"close_story_fail_{story_owner_username}")
            return False

    def check_for_challenge_or_block(self, context_for_screenshot="unknown_context"):
        """ Checks for common action block or challenge popups. """
        self.logger.debug("Checking for challenge or action block popups...")
        
        # Check for Action Block
        # Note: Ensure selector is specific enough not to match normal text
        action_block_indicator = self._find_element("error_popups.action_blocked_text_indicator", timeout_override=2)
        if action_block_indicator and action_block_indicator.is_displayed(): # Check is_displayed for elements that might exist but be hidden
            self.logger.critical(f"CRITICAL: ACTION BLOCKED detected for {self.username}!")
            take_screenshot(self.driver, f"ACTION_BLOCK_{context_for_screenshot}")
            # Try to click OK if an OK button selector is defined
            self._click_element("error_popups.error_popup_ok_button", "Action Block OK button", timeout_override=2)
            return "action_block"

        # Check for Challenge Required
        challenge_indicator = self._find_element("error_popups.challenge_required_indicator", timeout_override=2)
        if challenge_indicator and challenge_indicator.is_displayed():
            self.logger.critical(f"CRITICAL: CHALLENGE REQUIRED detected for {self.username}!")
            take_screenshot(self.driver, f"CHALLENGE_{context_for_screenshot}")
            # This requires manual intervention. Bot should pause or stop for this account.
            return "challenge_required"
            
        self.logger.debug("No common block or challenge popups detected.")
        return None # No specific known block/challenge found

    def quit_driver(self):
        if self.driver:
            self.logger.info("Attempting to quit WebDriver...")
            try:
                self.driver.quit()
                self.logger.info("WebDriver quit successfully.")
            except Exception as e:
                self.logger.error(f"Error during WebDriver quit: {e}")
            finally:
                self.driver = None # Ensure driver is None after attempting quit
        else:
            self.logger.info("WebDriver already None, no action needed for quit.")
