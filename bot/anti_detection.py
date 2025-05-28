import time
import random
import os
from .utils import get_logger, get_config # Use . for relative import

_USER_AGENTS_CACHE = []

def load_user_agents():
    global _USER_AGENTS_CACHE
    logger = get_logger()
    if not _USER_AGENTS_CACHE: # Load only once
        config = get_config()
        if not config:
            logger.error("Config not loaded, cannot get user_agent_file path.")
            return []
        
        ua_file_rel_path = config.get('AntiDetection', 'user_agent_file', fallback='config/user_agents.txt')
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # hsecurities_engagement_booster/
        ua_file_abs_path = os.path.join(project_root, ua_file_rel_path)

        try:
            with open(ua_file_abs_path, 'r', encoding='utf-8') as f:
                _USER_AGENTS_CACHE = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if not _USER_AGENTS_CACHE:
                logger.warning(f"User agent file '{ua_file_abs_path}' is empty or all lines commented out. Using Selenium default UA.")
        except FileNotFoundError:
            logger.warning(f"User agent file '{ua_file_abs_path}' not found. Using Selenium default UA.")
    return _USER_AGENTS_CACHE

def get_random_user_agent():
    user_agents = load_user_agents()
    if user_agents:
        return random.choice(user_agents)
    return None # Fallback to WebDriver default

def human_delay(action_type="default", min_override=None, max_override=None):
    logger = get_logger()
    config = get_config()
    if not config:
        logger.warning("Config not loaded for human_delay. Using hardcoded fallback delays.")
        time.sleep(random.uniform(2.0, 5.0)) # Fallback
        return

    if min_override is not None and max_override is not None:
        min_d, max_d = min_override, max_override
    elif action_type == "navigation":
        min_d = config.getfloat('AntiDetection', 'min_navigation_delay', fallback=1.8)
        max_d = config.getfloat('AntiDetection', 'max_navigation_delay', fallback=4.5)
    elif action_type == "story_view": # Specific delay for "watching" a story segment
        min_d = config.getfloat('AntiDetection', 'min_story_view_duration_s', fallback=2.5)
        max_d = config.getfloat('AntiDetection', 'max_story_view_duration_s', fallback=6.0)
    else: # Default human action delay
        min_d = config.getfloat('AntiDetection', 'min_human_action_delay', fallback=3.0)
        max_d = config.getfloat('AntiDetection', 'max_human_action_delay', fallback=7.0)

    if min_d < 0 or max_d < 0 or min_d > max_d: # Sanity check
        logger.warning(f"Invalid delay values for {action_type}: min={min_d}, max={max_d}. Using default 2-5s.")
        min_d, max_d = 2.0, 5.0
        
    actual_delay = random.uniform(min_d, max_d)
    logger.debug(f"Human delay ({action_type}): {actual_delay:.2f}s")
    time.sleep(actual_delay)

def type_like_human(element, text_to_type):
    logger = get_logger()
    config = get_config()
    if not config:
        logger.warning("Config not loaded for type_like_human. Using direct send_keys.")
        element.send_keys(text_to_type)
        return

    min_typing_ms = config.getint('AntiDetection', 'min_typing_delay_ms', fallback=60)
    max_typing_ms = config.getint('AntiDetection', 'max_typing_delay_ms', fallback=200)

    for char_to_type in text_to_type:
        element.send_keys(char_to_type)
        char_delay_ms = random.randint(min_typing_ms, max_typing_ms)
        time.sleep(char_delay_ms / 1000.0)
    human_delay("default") # A small pause after finishing typing

def apply_browser_fingerprint_tweaks(options):
    logger = get_logger()
    logger.debug("Applying browser fingerprint tweaks (basic)...")
    # Common resolutions (can be randomized or set from config)
    # resolutions = ["1366x768", "1920x1080", "1440x900", "1600x900"]
    # options.add_argument(f"--window-size={random.choice(resolutions)}")
    options.add_argument("--window-size=1366,768") # Fixed for consistency now
    options.add_argument("--lang=en-US,en;q=0.9") # Common browser language
    
    # These are often debated for effectiveness with modern Chrome/ChromeDriver
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Disable features that might reveal automation
    options.add_argument("--disable-blink-features=AutomationControlled")
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2 # Block notifications
    }
    options.add_experimental_option("prefs", prefs)
    # For more advanced stealth, consider using undetected_chromedriver and its specific options.


# --- Other Anti-Detection Strategies (Placeholders/Conceptual) ---
def should_perform_warmup(account_username):
    logger = get_logger()
    config = get_config()
    if not config or not config.getboolean('AntiDetection', 'enable_session_warmup', fallback=False):
        return False
    # TODO: Implement logic to check if this account (username) is "new" to the bot
    # or hasn't run in a while. This might involve storing last run timestamps
    # in a local file or small DB associated with the username.
    logger.info(f"Warmup check for {account_username} (placeholder: currently based on global config).")
    return True # For now, assume warmup if enabled globally

def get_warmup_action_multiplier(current_warmup_day_for_account):
    # TODO: current_warmup_day_for_account needs to be tracked per account
    logger = get_logger()
    config = get_config()
    if not config: return 1.0 # No config, no warmup adjustment

    total_warmup_days = config.getint('AntiDetection', 'warmup_days', fallback=3)
    initial_percentage = config.getfloat('AntiDetection', 'warmup_initial_action_percentage', fallback=0.2)

    if current_warmup_day_for_account <= 0:
        multiplier = initial_percentage
    elif current_warmup_day_for_account >= total_warmup_days:
        multiplier = 1.0 # Full actions
    else:
        # Simple linear increase for example
        progress = float(current_warmup_day_for_account) / total_warmup_days
        multiplier = initial_percentage + (1.0 - initial_percentage) * progress
    
    logger.debug(f"Warmup multiplier for day {current_warmup_day_for_account}: {multiplier:.2f}")
    return max(0.0, min(1.0, multiplier)) # Clamp between 0 and 1
