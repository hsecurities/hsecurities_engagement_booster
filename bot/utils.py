import time
import random
import logging
import configparser
import os
import yaml # For selectors
from selenium.webdriver.common.by import By

_SELECTORS_CACHE = None
_CONFIG_CACHE = None
_LOGGER_INSTANCE = None

# --- Configuration ---
def get_config(config_file_path=None): # Allow overriding default path
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        if config_file_path is None: # If no path given, use default
            config_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'user_config.ini')


        if not os.path.exists(config_file_path):
            tpl_path = os.path.join(os.path.dirname(config_file_path), 'user_config.ini.template')
            if os.path.exists(tpl_path):
                print(f"FATAL: Configuration file '{config_file_path}' not found. "
                      f"Please copy '{tpl_path}' to '{config_file_path}' and fill in your details.")
            else:
                print(f"FATAL: Configuration file '{config_file_path}' not found and no template available at '{tpl_path}'.")
            return None # Or raise an exception
        _CONFIG_CACHE = configparser.ConfigParser(interpolation=None) # Disable interpolation for raw values
        _CONFIG_CACHE.read(config_file_path, encoding='utf-8')
    return _CONFIG_CACHE

# --- Logging ---
def get_logger(name="hSECU_Bot"): # Shortened name for logs
    global _LOGGER_INSTANCE
    if _LOGGER_INSTANCE is None:
        config = get_config()
        if not config: # Critical if config fails to load
             # Fallback basic logger if config fails
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
            _LOGGER_INSTANCE = logging.getLogger(name)
            _LOGGER_INSTANCE.error("Logger initialized with fallback: Config failed to load.")
            return _LOGGER_INSTANCE

        log_level_str = config.get('GeneralSettings', 'log_level', fallback='INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        log_file = os.path.join(logs_dir, 'activity.log')

        _LOGGER_INSTANCE = logging.getLogger(name)
        _LOGGER_INSTANCE.setLevel(log_level) # Set level on the logger itself

        # Prevent adding multiple handlers if called again (e.g. in tests)
        if not _LOGGER_INSTANCE.hasHandlers():
            # File Handler
            fh = logging.FileHandler(log_file, encoding='utf-8', mode='a') # Append mode
            fh.setLevel(log_level)
            # Console Handler
            ch = logging.StreamHandler()
            ch.setLevel(log_level)

            formatter = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)

            _LOGGER_INSTANCE.addHandler(fh)
            _LOGGER_INSTANCE.addHandler(ch)
    return _LOGGER_INSTANCE

# --- Selectors ---
def get_selector(key_path, selectors_file_rel_path='config/selectors.yaml'):
    global _SELECTORS_CACHE
    logger = get_logger() # Ensure logger is initialized

    # Construct absolute path for selectors.yaml relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    selectors_file_abs_path = os.path.join(project_root, selectors_file_rel_path)

    if _SELECTORS_CACHE is None:
        try:
            with open(selectors_file_abs_path, 'r', encoding='utf-8') as f:
                _SELECTORS_CACHE = yaml.safe_load(f)
        except FileNotFoundError:
            logger.critical(f"Selectors file '{selectors_file_abs_path}' not found!")
            _SELECTORS_CACHE = {} # Avoid repeated attempts if file is missing
            return None, None # Return tuple
        except yaml.YAMLError as e:
            logger.critical(f"Error parsing selectors YAML file '{selectors_file_abs_path}': {e}")
            _SELECTORS_CACHE = {}
            return None, None # Return tuple

    keys = key_path.split('.')
    data = _SELECTORS_CACHE
    current_path_trace = []
    for key in keys:
        current_path_trace.append(key)
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            logger.error(f"Selector key part '{key}' not found in path '{'.'.join(current_path_trace)}' in '{selectors_file_abs_path}'. Current data segment: {data}")
            return None, None # Return tuple

    if isinstance(data, dict) and 'type' in data and 'value' in data:
        by_type_str = data['type'].upper()
        selector_value = data['value']
        by_mapping = {
            "XPATH": By.XPATH, "CSS_SELECTOR": By.CSS_SELECTOR, "ID": By.ID,
            "NAME": By.NAME, "CLASS_NAME": By.CLASS_NAME, "TAG_NAME": By.TAG_NAME,
            "LINK_TEXT": By.LINK_TEXT, "PARTIAL_LINK_TEXT": By.PARTIAL_LINK_TEXT,
        }
        if by_type_str in by_mapping:
            return by_mapping[by_type_str], selector_value
        else:
            logger.error(f"Invalid selector type '{data['type']}' for key '{key_path}' in '{selectors_file_abs_path}'.")
            return None, None # Return tuple
    else:
        logger.error(f"Selector data for '{key_path}' in '{selectors_file_abs_path}' is not in the expected format {{type: ..., value: ...}}. Found: {data}")
        return None, None # Return tuple

# --- Helper ---
def get_list_from_config_string(config_string):
    if not config_string: return []
    return [item.strip().lower() for item in config_string.split(',') if item.strip()]

def take_screenshot(driver, filename_prefix="error"):
    logger = get_logger()
    config = get_config()
    if not driver:
        logger.warning("Attempted to take screenshot, but driver is None.")
        return

    if not config or not config.getboolean('ErrorHandling', 'screenshot_on_error', fallback=False):
        return

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    screenshot_rel_path = config.get('ErrorHandling', 'error_screenshot_path', fallback='.errors/')
    screenshot_abs_path = os.path.join(project_root, screenshot_rel_path)

    if not os.path.exists(screenshot_abs_path):
        try:
            os.makedirs(screenshot_abs_path)
        except OSError as e:
            logger.error(f"Could not create screenshot directory {screenshot_abs_path}: {e}")
            return
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    # Sanitize filename_prefix
    safe_prefix = "".join(c if c.isalnum() else "_" for c in filename_prefix)
    filepath = os.path.join(screenshot_abs_path, f"{safe_prefix}_{timestamp}.png")
    try:
        driver.save_screenshot(filepath)
        logger.info(f"Screenshot saved: {filepath}")
    except Exception as e:
        logger.error(f"Failed to take screenshot to {filepath}: {e}")

if __name__ == '__main__': # Basic test
    logger = get_logger() # Initialize logger via get_logger
    config = get_config() # Initialize config via get_config
    if config:
        logger.info(f"Tool Name from config: {config.get('Branding', 'tool_name', fallback='N/A')}")
    
    sel_type, sel_val = get_selector("login_page.username_field")
    if sel_type:
        logger.info(f"Test selector for username: {sel_type}, {sel_val}")
    else:
        logger.warning("Failed to get username selector for testing.")
    logger.info("Utils test complete.")
