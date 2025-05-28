import argparse
import sys
import getpass # For securely prompting for password

# Initialize utils first to set up logger and config loading
from bot.utils import get_logger, get_config, take_screenshot
from bot.instagram_bot import InstagramBot
from bot.actions import EngagementActions
from licensing.license_validator import LicenseValidator
from bot.anti_detection import human_delay # For pauses

def run_bot():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="hSECURITIES Instagram Engagement Booster")
    parser.add_argument("--config", default="config/user_config.ini", help="Path to the configuration file.")
    parser.add_argument("--mode", choices=["like", "story_view", "both", "feed_stories"], default="both",
                        help="Engagement mode for hashtag/user targets, or 'feed_stories'.")
    parser.add_argument("--target-type", choices=["hashtag", "user_followers"], default="hashtag",
                        help="Type of target for engagement (user_followers is PRO only).")
    parser.add_argument("--targets", help="Comma-separated list of targets (e.g., 'travel,food' or 'user1,user2').")
    parser.add_argument("--skip-login-prompt", action="store_true", help="Skip password prompt if password is not in config (NOT RECOMMENDED).")


    args = parser.parse_args()

    # --- Initialize Core Components (Logger and Config first) ---
    config = get_config(args.config) # Load config via util
    if not config:
        # Logger might not be available yet if config load failed badly
        print(f"FATAL: Could not load configuration from {args.config}. Exiting.")
        sys.exit(1)

    logger = get_logger() # Now logger is safe to use
    tool_brand = config.get('Branding', 'tool_name', fallback='hSECURITIES Engagement Booster')
    tool_version = config.get('Branding', 'version', fallback='N/A')

    logger.info(f"--- Starting {tool_brand} v{tool_version} ---")
    logger.info("CRITICAL WARNING: Instagram automation is against ToS. Use responsibly and at your OWN RISK with BURNER ACCOUNTS initially.")
    human_delay("default")

    # --- Credentials ---
    username = config.get('Credentials', 'username', fallback=None)
    password_from_config = config.get('Credentials', 'password', fallback=None)
    password_is_prompted = False

    if not username:
        logger.critical("Instagram username not found in configuration. Please set it.")
        sys.exit(1)

    actual_password_to_use = password_from_config
    if not actual_password_to_use and not args.skip_login_prompt:
        logger.info(f"Password for '{username}' not found in config. Prompting...")
        try:
            actual_password_to_use = getpass.getpass(f"Enter Instagram password for {username}: ")
            password_is_prompted = True
        except Exception as e:
            logger.critical(f"Could not read password from prompt: {e}")
            sys.exit(1)
    elif not actual_password_to_use and args.skip_login_prompt:
        logger.critical(f"Password for '{username}' not set and prompt skipped. Cannot proceed.")
        sys.exit(1)

    # --- License Validation ---
    license_val = LicenseValidator()
    is_pro_active = license_val.is_pro_license_active()

    # --- Initialize Bot ---
    insta_bot = InstagramBot(username, password_is_prompted=password_is_prompted)
    insta_bot.set_pro_status(is_pro_active) # Inform bot instance about pro status for proxy etc.

    if not insta_bot.initialize_driver(): # This sets up Selenium driver
        logger.critical("Failed to initialize WebDriver. Exiting.")
        sys.exit(1)

    # Pass the actual password to the login method if it was prompted or needs to be re-fetched
    # The InstagramBot.login() method now handles fetching password if not directly passed or set
    # For simplicity, we assume the InstagramBot's constructor and login are designed to handle this.
    # If InstagramBot.login() needs password explicitly:
    # if not insta_bot.login(password=actual_password_to_use): # Modify login to accept it
    if not insta_bot.login(): # Current InstagramBot.login fetches password if needed
        logger.critical("Instagram login failed. Exiting.")
        # Password variable should be cleared if it was in memory
        actual_password_to_use = "" # Clear password from memory
        insta_bot.quit_driver()
        sys.exit(1)
    
    actual_password_to_use = "" # Clear password from memory after successful login attempt

    # --- Perform Actions ---
    actions_manager = EngagementActions(insta_bot, is_pro_active)
    try:
        if args.mode == "feed_stories":
            actions_manager.view_feed_stories()
        elif args.target_type == "hashtag":
            if not args.targets:
                logger.error("No hashtags provided. Use --targets 'hash1,hash2'.")
            else:
                actions_manager.engage_with_hashtags(args.targets, mode=args.mode)
        elif args.target_type == "user_followers":
            if not is_pro_active:
                logger.warning("Targeting user followers is a PRO feature. Get a license to enable.")
            elif not args.targets:
                logger.error("No target users provided. Use --targets 'user1,user2'.")
            else:
                actions_manager.engage_with_user_followers(args.targets, mode=args.mode)
        else:
            logger.warning(f"Unsupported target type: {args.target_type}")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down gracefully...")
    except Exception as e_main:
        logger.critical(f"An unhandled error occurred in the main execution block: {e_main}", exc_info=True)
        if insta_bot and insta_bot.driver:
            take_screenshot(insta_bot.driver, "main_execution_error")
    finally:
        if actions_manager: # Check if it was initialized
            actions_manager.print_summary()
        if insta_bot:
            insta_bot.quit_driver()
        
        pause_min = config.getint('AntiDetection', 'pause_between_sessions_min_minutes', fallback=5)
        pause_max = config.getint('AntiDetection', 'pause_between_sessions_max_minutes', fallback=15)
        actual_pause_seconds = random.randint(pause_min * 60, pause_max * 60)
        logger.info(f"--- {tool_brand} Finished ---")
        logger.info(f"Script will pause for approximately {actual_pause_seconds // 60} minutes before full exit (simulating session end). Press Ctrl+C to exit now.")
        try:
            time.sleep(actual_pause_seconds)
        except KeyboardInterrupt:
            logger.info("Exiting immediately due to second interrupt.")

if __name__ == "__main__":
    run_bot()
