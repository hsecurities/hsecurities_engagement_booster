import time
import random
import os
from .utils import get_logger, get_config

_USER_AGENTS_CACHE = []

def load_user_agents():
    global _USER_AGENTS_CACHE
    if not _USER_AGENTS_CACHE:
        config = get_config()
        ua_file = config.get('AntiDetection', 'user_agent_file', fallback='config/user_agents.txt')
        try:
            with open(ua_file, 'r', encoding='utf-8') as f:
                _USER_AGENTS_CACHE = [line.strip() for line in f if line.strip()]
            if not _USER_AGENTS_CACHE:
                get_logger().warning(f"User agent file '{ua_file}' is empty or not found. Using Selenium default.")
        except FileNotFoundError:
            get_logger().warning(f"User agent file '{ua_file}' not found. Using Selenium default.")
    return _USER_AGENTS_CACHE

def get_random_user_agent():
    user_agents = load_user_agents()
    if user_agents:
        return random.choice(user_agents)
    return None # Fallback to WebDriver default

def human_delay(action_type="default"):
    """More sophisticated delay based on action type and config."""
    logger = get_logger()
    config = get_config()
    # Default to general action delays
    min_d = config.getfloat('AntiDetection', 'min_human_action_delay', fallback=2.0)
    max_d = config.getfloat('AntiDetection', 'max_human_action_delay', fallback=5.0)

    if action_type == "navigation":
        min_d = config.getfloat('AntiDetection', 'min_navigation_delay', fallback=1.0)
        max_d = config.getfloat('AntiDetection', 'max_navigation_delay', fallback=3.0)
    elif action_type == "typing": # This delay is per key, handled differently
        min_d_ms = config.getint('AntiDetection', 'min_typing_delay_ms', fallback=50)
        max_d_ms = config.getint('AntiDetection', 'max_typing_delay_ms', fallback=150)
        delay_ms = random.randint(min_d_ms, max_d_ms)
        time.sleep(delay_ms / 1000.0)
        return # Typing delay is per char, not a block
    # Add more action_types if needed: "like", "scroll", "story_view"

    actual_delay = random.uniform(min_d, max_d)
    logger.debug(f"Human delay ({action_type}): {actual_delay:.2f}s")
    time.sleep(actual_delay)

def type_like_human(element, text):
    """Types text into an element char by char with small random delays."""
    for char in text:
        element.send_keys(char)
        human_delay(action_type="typing") # This will call time.sleep for a few ms
    human_delay(action_type="default") # A slightly longer pause after typing all

# --- Other Anti-Detection Strategies (Placeholders) ---
def apply_browser_fingerprint_tweaks(options):
    logger = get_logger()
    logger.info("Applying browser fingerprint tweaks (placeholder)...")
    # Examples:
    # options.add_argument("--window-size=1366,768") # Common resolution
    # options.add_argument("--lang=en-US,en;q=0.9")
    # options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # options.add_experimental_option('useAutomationExtension', False)
    # Potentially use undetected_chromedriver options here if integrated
    pass

def should_perform_warmup(account_identifier):
    # Placeholder: Check if this account is new or hasn't run in a while
    # Might involve checking a local file or database for last run timestamp
    config = get_config()
    return config.getboolean('AntiDetection', 'enable_session_warmup', fallback=False)

def get_warmup_action_multiplier(current_warmup_day):
    # Placeholder: Calculate how many actions to perform based on warmup progress
    config = get_config()
    total_warmup_days = config.getint('AntiDetection', 'warmup_days', fallback=3)
    initial_percentage = config.getfloat('AntiDetection', 'warmup_initial_action_percentage', fallback=0.2)
    if current_warmup_day <= 0: return initial_percentage
    if current_warmup_day >= total_warmup_days: return 1.0 # Full actions
    
    # Simple linear increase
    progress = current_warmup_day / total_warmup_days
    return initial_percentage + (1.0 - initial_percentage) * progress
