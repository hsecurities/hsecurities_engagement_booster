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
def get_config(config_file_path='config/user_config.ini'):
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        if not os.path.exists(config_file_path):
            tpl_path = 'config/user_config.ini.template'
            if os.path.exists(tpl_path):
                print(f"Warning: {config_file_path} not found. Please copy '{tpl_path}' to '{config_file_path}' and fill in your details.")
            else:
                print(f"Error: {config_file_path} not found and no template available.")
            return None # Or raise an exception
        _CONFIG_CACHE = configparser.ConfigParser()
        _CONFIG_CACHE.read(config_file_path)
    return _CONFIG_CACHE

# --- Logging ---
def get_logger(name="hSECURITIES Bot"):
    global _LOGGER_INSTANCE
    if _LOGGER_INSTANCE is None:
        config = get_config()
        log_level_str = config.get('GeneralSettings', 'log_level', fallback='INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

        if not os.path.exists('logs'):
            os.makedirs('logs')
        log_file = os.path.join('logs', 'activity.log')

        _LOGGER_INSTANCE = logging.getLogger(name)
        _LOGGER_INSTANCE.setLevel(log_level)

        # File Handler
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(log_level)
        # Console Handler
        ch = logging.StreamHandler()
        ch.setLevel(log_level) # Or a different level for console

        formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        if not _LOGGER_INSTANCE.hasHandlers():
            _LOGGER_INSTANCE.addHandler(fh)
            _LOGGER_INSTANCE.addHandler(ch)
    return _LOGGER_INSTANCE

# --- Selectors ---
def get_selector(key_path, selectors_file='config/selectors.yaml'):
    global _SELECTORS_CACHE
    logger = get_logger()
    if _SELECTORS_CACHE is None:
        try:
            with open(selectors_file, 'r', encoding='utf-8') as f:
                _SELECTORS_CACHE = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Selectors file '{selectors_file}' not found!")
            _SELECTORS_CACHE = {}
            return None
        except yaml.YAMLError as e:
            logger.error(f"Error parsing selectors YAML file '{selectors_file}': {e}")
            _SELECTORS_CACHE = {}
            return None

    keys = key_path.split('.')
    data = _SELECTORS_CACHE
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            logger.warning(f"Selector key part '{key}' not found in path '{key_path}'. Current data: {data}")
            return None

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
            logger.warning(f"Invalid selector type '{data['type']}' for key '{key_path}'.")
            return None
    else:
        logger.warning(f"Selector data for '{key_path}' is not in the expected format {{type: ..., value: ...}} in '{selectors_file}'. Data: {data}")
        return None

# --- Helper ---
def get_list_from_config_string(config_string):
    if not config_string: return []
    return [item.strip().lower() for item in config_string.split(',') if item.strip()]

def take_screenshot(driver, filename_prefix="error"):
    logger = get_logger()
    config = get_config()
    if not config.getboolean('ErrorHandling', 'screenshot_on_error', fallback=False):
        return

    path = config.get('ErrorHandling', 'error_screenshot_path', fallback='.errors/')
    if not os.path.exists(path):
        os.makedirs(path)
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filepath = os.path.join(path, f"{filename_prefix}_{timestamp}.png")
    try:
        driver.save_screenshot(filepath)
        logger.info(f"Screenshot saved to {filepath}")
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")

if __name__ == '__main__': # Basic test
    logger = get_logger()
    config = get_config()
    if config:
        logger.info(f"Tool Name from config: {config.get('Branding', 'tool_name', fallback='N/A')}")
    
    sel_type, sel_val = get_selector("login_page.username_field")
    if sel_type:
        logger.info(f"Test selector for username: {sel_type}, {sel_val}")
    else:
        logger.warning("Failed to get username selector for testing.")
