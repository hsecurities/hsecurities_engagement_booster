import argparse
import sys
import getpass # For securely prompting for password
import time # For final pause
import random # For final pause
import os # For path joining if needed

# Initialize utils first to set up logger and config loading
# Ensure 'bot' and 'licensing' are in PYTHONPATH or handle imports carefully
try:
    from bot.utils import get_logger, get_config, take_screenshot
    from bot.instagram_bot import InstagramBot
    from bot.actions import EngagementActions
    from licensing.license_validator import LicenseValidator
    from bot.anti_detection import human_delay # For pauses
except ImportError as e:
    # This can happen if script is not run from project root or venv not active
    print(f"ImportError: {e}. Please ensure you are running from the project root directory "
          "and your virtual environment is activated with all dependencies installed.")
    sys.exit(1)

def run_bot():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="hSECURITIES Instagram Engagement Booster",
        formatter_class=argparse.RawTextHelpFormatter # For better help text formatting
    )
    parser.add_argument(
        "--config", 
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'user_config.ini'), # Default config relative to main.py
        help="Path to the configuration file."
    )
    parser.add_argument(
        "--mode", 
        choices=["like", "story_view", "both", "feed_stories"], 
        default="both",
        help="Engagement mode for hashtag/user targets, or 'feed_stories'.\n"
             "  like: Only like posts.\n"
             "  story_view: Only view stories (for relevant targets).\n"
             "  both: Perform both liking and story viewing (default).\n"
             "  feed_stories: View stories from your home feed."
    )
    parser.add_argument(
        "--target-type", 
        choices=["hashtag", "user_followers"], 
        default="hashtag",
        help="Type of target for engagement.\n"
             "  hashtag: Engage with content from specified hashtags (default).\n"
             "  user_followers: (PRO Placeholder) Engage with followers of specified users."
    )
    parser.add_argument(
        "--targets", 
        help="Comma-separated list of targets (e.g., 'travel,food' or 'user1,user2'). Required for 'hashtag' or 'user_followers' target types."
    )
    parser.add_argument(
        "--skip-password-prompt", 
        action="store_true", 
        help="Skip password prompt if password is not in config. The bot will fail to login if password is not set."
    )

    args = parser.parse_args()

    # --- Initialize Core Components (Config and Logger first) ---
    config = get_config(args.config) # Load config via util, passing path from args
    if not config:
        # Logger might not be available yet if config load failed badly
        print(f"FATAL: Could not load configuration from {args.config}. Ensure the file exists and is readable. Exiting.")
        sys.exit(1)

    logger = get_logger() # Now logger is safe to use
    tool_brand = config.get('Branding', 'tool_name', fallback='hSECURITIES Engagement Booster')
    tool_version = config.get('Branding', 'version', fallback='N/A')

    logger.info(f"--- Starting {tool_brand} v{tool_version} ---")
    logger.critical("CRITICAL WARNING: Instagram automation is against ToS. Use responsibly and at your OWN RISK with BURNER ACCOUNTS initially.")
    human_delay("default", min_override=1, max_override=2) # Small startup pause

    # --- Credentials ---
    username = config.get('Credentials', 'username', fallback=None)
    password_from_config = config.get('Credentials', 'password', fallback=None)
    
    actual_password_to_use = None # Will hold the password for login
    password_was_prompted = False

    if not username or not username.strip():
        logger.critical("Instagram username not found or empty in configuration. Please set it in [Credentials] username.")
        sys.exit(1)

    if password_from_config and password_from_config.strip():
        logger.info(f"Using password for '{username}' from configuration file (less secure).")
        actual_password_to_use = password_from_config
    elif not args.skip_password_prompt:
        logger.info(f"Password for '{username}' not found in config or is empty. Prompting...")
        try:
            actual_password_to_use = getpass.getpass(f"Enter Instagram password for {username}: ")
            password_was_prompted = True
            if not actual_password_to_use: # User pressed Enter without typing
                logger.critical("Password not entered at prompt. Cannot proceed.")
                sys.exit(1)
        except Exception as e_getpass: # Catch potential issues with getpass (e.g., no tty)
            logger.critical(f"Could not read password from prompt: {e_getpass}. "
                            "Try running in a proper terminal or set password in config (less secure).")
            sys.exit(1)
    else: # skip_password_prompt is True and password not in config
        logger.critical(f"Password for '{username}' not set in config and prompt was skipped. Cannot login.")
        sys.exit(1)

    # --- License Validation ---
    license_val = LicenseValidator()
    is_pro_active = license_val.is_pro_license_active()
    if is_pro_active:
        logger.info("Pro license detected and validated (placeholder). Pro features will be attempted.")
    else:
        logger.info("Running in Demo mode (no valid Pro license found). Limits and features will be restricted.")


    # --- Initialize Bot ---
    insta_bot = None # Define before try block for finally clause
    actions_manager = None
    try:
        insta_bot = InstagramBot(
            username, 
            password_was_prompted=password_was_prompted, 
            external_password=actual_password_to_use if password_was_prompted else None
        )
        # Pass pro status to bot instance AFTER it's initialized (so it can use logger/config)
        insta_bot.set_pro_status(is_pro_active)

        if not insta_bot.initialize_driver():
            logger.critical("Failed to initialize WebDriver. Please check logs for errors (e.g., Chrome/ChromeDriver versions). Exiting.")
            sys.exit(1)

        # Clear password from memory immediately after passing it (or after bot uses it)
        actual_password_to_use = "****************" # Obfuscate in memory

        if not insta_bot.login(): # Login method now handles getting password if needed
            logger.critical("Instagram login failed. Please check credentials, network, and for any Instagram challenges (e.g., 2FA, suspicious login prompts). Exiting.")
            sys.exit(1) # Exit after bot.quit_driver() is called in finally
        
        # --- Perform Actions ---
        actions_manager = EngagementActions(insta_bot, is_pro_active) # Pass initialized bot and pro status

        if (args.target_type == "hashtag" or args.target_type == "user_followers") and not args.targets:
            logger.error(f"Target type '{args.target_type}' requires --targets to be specified. Example: --targets \"target1,target2\"")
        elif args.mode == "feed_stories":
            actions_manager.view_feed_stories()
        elif args.target_type == "hashtag":
            actions_manager.engage_with_hashtags(args.targets, engagement_mode=args.mode)
        elif args.target_type == "user_followers":
            # Pro check is also inside the method, but good to have one here too for user feedback
            if not is_pro_active:
                logger.warning("Targeting user followers is a PRO feature. This action will be skipped. Please obtain a Pro license.")
            else:
                actions_manager.engage_with_user_followers(args.targets, engagement_mode=args.mode)
        else:
            logger.warning(f"Unsupported target type or mode combination: target_type='{args.target_type}', mode='{args.mode}'")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down gracefully...")
    except Exception as e_main_execution:
        logger.critical(f"An unhandled error occurred in the main execution block: {e_main_execution}", exc_info=True)
        if insta_bot and insta_bot.driver: # Check if driver exists before trying to screenshot
            take_screenshot(insta_bot.driver, "main_critical_error")
    finally:
        if actions_manager: # Check if it was initialized
            actions_manager.print_summary()
        
        if insta_bot: # Ensure insta_bot was initialized
            insta_bot.quit_driver() # Handles if driver is None
        
        if config: # Check if config was loaded for final pause
            pause_min_m = config.getint('AntiDetection', 'pause_between_sessions_min_minutes', fallback=1)
            pause_max_m = config.getint('AntiDetection', 'pause_between_sessions_max_minutes', fallback=5)
            # Ensure min is not greater than max
            if pause_min_m > pause_max_m: pause_min_m = pause_max_m 
            actual_pause_seconds = random.randint(max(0, pause_min_m * 60), max(1, pause_max_m * 60))
            
            logger.info(f"--- {tool_brand} Session Finished ---")
            if actual_pause_seconds > 0 :
                logger.info(f"Script will pause for approximately {actual_pause_seconds // 60} minute(s) and {actual_pause_seconds % 60} second(s) before full exit.")
                logger.info("This simulates a natural session end. Press Ctrl+C to exit immediately.")
                try:
                    time.sleep(actual_pause_seconds)
                except KeyboardInterrupt:
                    logger.info("Exiting immediately due to interrupt during final pause.")
            else:
                logger.info("No final pause configured or pause duration is zero.")
        else:
            logger.info(f"--- {tool_brand} Session Finished (Config not loaded for final pause) ---")
        
        logger.info("Application terminated.")

if __name__ == "__main__":
    # Check if running as main script before attempting to change current working directory
    # This helps if utils.py or other modules are imported by tests or other scripts
    # For the main entry point, it's usually fine as paths are relative to it.
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # if os.getcwd() != script_dir:
    #     os.chdir(script_dir) # Change CWD to script's dir for consistent relative paths
    #     print(f"Changed CWD to: {script_dir}")
    run_bot()
