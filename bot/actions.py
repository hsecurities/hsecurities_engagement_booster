from .utils import get_logger, get_config, get_list_from_config_string, take_screenshot # Relative
from .anti_detection import human_delay, should_perform_warmup, get_warmup_action_multiplier # Relative

class EngagementActions:
    def __init__(self, bot_instance, is_pro_user_status): # Pass initialized bot
        self.bot = bot_instance # Instance of InstagramBot
        self.logger = get_logger()
        self.config = get_config()
        self.is_pro = is_pro_user_status # Boolean

        self.current_run_limits = {}
        self.action_counts = {"likes": 0, "story_views": 0, "targets_processed": 0}
        
        # Warmup state (conceptual, needs per-account tracking if truly used)
        self.is_warmup_active_for_session = False
        self.current_warmup_day = 0 # This should be loaded/saved per account

        self._load_run_limits_and_apply_warmup()

        self.blacklist_users = get_list_from_config_string(self.config.get('Blacklist', 'users_to_avoid', fallback=''))
        # self.blacklist_keywords = get_list_from_config_string(self.config.get('Blacklist', 'keywords_to_avoid', fallback=''))

    def _load_run_limits_and_apply_warmup(self):
        limit_section = 'ProSettings' if self.is_pro else 'DemoLimits'
        self.logger.info(f"Loading action limits from section: [{limit_section}]")

        self.current_run_limits['max_likes'] = self.config.getint(limit_section, 'max_likes_per_run', fallback=5)
        self.current_run_limits['max_story_views'] = self.config.getint(limit_section, 'max_story_views_per_run', fallback=8)
        self.current_run_limits['max_targets'] = self.config.getint(limit_section, 'max_targets_per_run', fallback=1)
        
        self.logger.info(f"Initial limits: Likes={self.current_run_limits['max_likes']}, Stories={self.current_run_limits['max_story_views']}, Targets={self.current_run_limits['max_targets']}")

        # Conceptual Warmup Application
        if self.config.getboolean('AntiDetection', 'enable_session_warmup', fallback=False):
            # In a real app, you'd load current_warmup_day from persistent storage for self.bot.username
            # For this example, let's assume it's the first day of warmup if enabled.
            self.current_warmup_day = 1 # Example: Start at day 1 of warmup
            self.is_warmup_active_for_session = True # Based on global config for now
            self.logger.info(f"Session Warmup is globally enabled. Applying for (conceptual) day {self.current_warmup_day}.")

        if self.is_warmup_active_for_session:
            multiplier = get_warmup_action_multiplier(self.current_warmup_day)
            self.current_run_limits['max_likes'] = int(self.current_run_limits['max_likes'] * multiplier)
            self.current_run_limits['max_story_views'] = int(self.current_run_limits['max_story_views'] * multiplier)
            # Targets limit might also be adjusted or stay fixed
            self.current_run_limits['max_targets'] = max(1, int(self.current_run_limits['max_targets'] * multiplier)) # Ensure at least 1 target if possible
            self.logger.info(f"Warmup active (Day {self.current_warmup_day}): Multiplier={multiplier:.2f}. Adjusted limits: Likes={self.current_run_limits['max_likes']}, Stories={self.current_run_limits['max_story_views']}, Targets={self.current_run_limits['max_targets']}")


    def _is_action_blocked_or_limit_reached(self, action_type_to_check):
        """Checks for IG blocks and internal action limits."""
        # Check for Instagram-imposed blocks first
        block_status = self.bot.check_for_challenge_or_block(f"before_{action_type_to_check}")
        if block_status == "action_block":
            self.logger.critical(f"ACTION BLOCK DETECTED. Stopping all '{action_type_to_check}' actions and potentially all further engagement for this session.")
            # You might want to set all limits to 0 to stop further actions
            self.current_run_limits['max_likes'] = self.action_counts["likes"] 
            self.current_run_limits['max_story_views'] = self.action_counts["story_views"]
            return True # Blocked
        elif block_status == "challenge_required":
            self.logger.critical("CHALLENGE REQUIRED. Bot cannot proceed. Manual intervention needed for this account.")
            # Stop all actions
            self.current_run_limits['max_likes'] = self.action_counts["likes"] 
            self.current_run_limits['max_story_views'] = self.action_counts["story_views"]
            return True # Blocked by challenge

        # Check internal limits
        if action_type_to_check == "like" and self.action_counts["likes"] >= self.current_run_limits['max_likes']:
            self.logger.info("Internal 'Like' limit reached for this run.")
            return True # Limit reached
        if action_type_to_check == "story_view" and self.action_counts["story_views"] >= self.current_run_limits['max_story_views']:
            self.logger.info("Internal 'Story View' limit reached for this run.")
            return True # Limit reached
        
        return False # Not blocked and limit not reached

    def _is_target_blacklisted(self, username_to_check):
        # Basic user blacklist check
        if not username_to_check: return False # Cannot blacklist if no username
        normalized_username = username_to_check.lower().strip()
        if normalized_username in self.blacklist_users:
            self.logger.info(f"User '{username_to_check}' is blacklisted. Skipping.")
            return True
        # TODO: Add keyword blacklist check for bios/captions if implemented (more complex)
        return False

    def engage_with_hashtags(self, hashtags_str, engagement_mode="both"):
        if not self.bot or not self.bot.driver:
            self.logger.error("Bot not properly initialized. Cannot perform hashtag engagement.")
            return

        hashtags_to_process = get_list_from_config_string(hashtags_str)
        if not hashtags_to_process:
            self.logger.warning("No valid hashtags provided for engagement.")
            return

        self.logger.info(f"Starting hashtag engagement (mode: {engagement_mode}) for: {', '.join(hashtags_to_process)}")

        for i, hashtag_name in enumerate(hashtags_to_process):
            if self.action_counts["targets_processed"] >= self.current_run_limits['max_targets']:
                self.logger.info(f"Max target limit ({self.current_run_limits['max_targets']}) reached. Stopping hashtag processing.")
                break
            
            self.logger.info(f"--- Processing hashtag #{hashtag_name} ({i+1}/{len(hashtags_to_process)}) ---")
            if not self.bot.navigate_to_url(f"/explore/tags/{hashtag_name.strip()}/"):
                self.logger.warning(f"Failed to navigate to hashtag #{hashtag_name}. Skipping.")
                continue # Skip to next hashtag

            self.action_counts["targets_processed"] += 1
            
            # Wait for recent posts section to be somewhat loaded (selector dependent)
            # self.bot._find_element("hashtag_page.recent_posts_section_header", timeout_override=10) # Example
            human_delay("navigation") # General pause after navigation

            # --- Liking Posts from Hashtag ---
            if engagement_mode in ["like", "both"]:
                if self._is_action_blocked_or_limit_reached("like"):
                    self.logger.info("Stopping 'like' actions for hashtags due to block or limit.")
                else:
                    self.logger.info(f"Looking for posts to like under #{hashtag_name}...")
                    # This needs a robust way to get post elements/links from hashtag page.
                    # Let's try to get a few thumbnail links.
                    # The selector needs to be for the <a> tags wrapping post thumbnails in the grid.
                    post_thumbnail_links = self.bot._find_elements("hashtag_page.post_thumbnail_link_in_recent_grid", timeout_override=10)
                    
                    if not post_thumbnail_links:
                        self.logger.warning(f"No post thumbnails found for #{hashtag_name} (check 'post_thumbnail_link_in_recent_grid' selector).")
                    else:
                        self.logger.info(f"Found {len(post_thumbnail_links)} potential post thumbnails for #{hashtag_name}.")
                        # Interact with a limited number of these, e.g., first 1-3
                        posts_to_process_this_hashtag = random.randint(1, max(1, min(3, len(post_thumbnail_links)))) # Example: 1 to 3 posts
                        
                        for post_idx, thumb_link_el in enumerate(post_thumbnail_links[:posts_to_process_this_hashtag]):
                            if self._is_action_blocked_or_limit_reached("like"): break # Re-check before each like

                            post_url = thumb_link_el.get_attribute("href")
                            if not post_url or "/p/" not in post_url:
                                self.logger.debug("Skipping non-post link from hashtag grid.")
                                continue

                            # TODO: Extract post owner username here if possible for blacklist check before clicking
                            # This is complex from just a thumbnail, usually done after opening post.

                            self.logger.info(f"Attempting to interact with post: {post_url}")
                            if self.bot._click_element(thumb_link_el, f"Post thumbnail {post_idx+1} for #{hashtag_name}"):
                                human_delay("navigation") # Wait for modal to open
                                if self.bot.like_post_in_modal(): # Assumes like_post_in_modal checks for already liked
                                    self.action_counts["likes"] += 1
                                else:
                                    self.logger.debug(f"Did not like post {post_url} (already liked or failed).")
                                
                                if not self.bot.close_post_modal():
                                    self.logger.warning(f"Failed to close post modal for {post_url}. Attempting to recover.")
                                    # Recovery: navigate back or to main page if modal is stuck
                                    self.bot.navigate_to_url("/") # Go home to reset state
                                    break # Stop processing this hashtag if modal gets stuck
                                human_delay("default") # Pause after closing modal
                            else:
                                self.logger.warning(f"Failed to click post thumbnail {post_idx+1} for #{hashtag_name}.")
                                break # If one fails, subsequent might also, skip to next hashtag
            
            # --- Story Viewing from Hashtag (Conceptual/Placeholder) ---
            # True story viewing by hashtag is complex: find users who posted with hashtag, then view their stories.
            if engagement_mode in ["story_view", "both"]:
                if self._is_action_blocked_or_limit_reached("story_view"):
                    self.logger.info("Stopping 'story_view' actions for hashtags due to block or limit.")
                else:
                    self.logger.info(f"Conceptual: Story viewing for hashtag #{hashtag_name} (not fully implemented).")
                    # Example: Find a user from one of the posts just interacted with (if info available)
                    # and attempt to view their story if they have one.
                    # This would require extracting username from post modal, navigating to profile, then checking story ring.
                    # self.action_counts["story_views"] += N # Increment if stories are viewed

            # Check if all global limits reached after processing one hashtag
            if (self.action_counts["likes"] >= self.current_run_limits['max_likes'] and
                self.action_counts["story_views"] >= self.current_run_limits['max_story_views']):
                self.logger.info("All primary action limits reached. Ending hashtag engagement.")
                break # Break from hashtags loop
            
            human_delay("navigation", min_override=5, max_override=10) # Longer delay between processing different hashtags

    def view_feed_stories(self):
        if not self.bot or not self.bot.driver:
            self.logger.error("Bot not properly initialized. Cannot view feed stories.")
            return
            
        self.logger.info("Attempting to view stories from home feed.")
        if not self.bot.navigate_to_url("/"): # Navigate to home feed
            self.logger.error("Failed to navigate to home feed.")
            return

        stories_viewed_this_action = 0
        
        # The selector "story_viewer.story_ring_on_feed_list" should return a list of story ring elements
        story_ring_elements = self.bot._find_elements("story_viewer.story_ring_on_feed_list", timeout_override=10)
        
        if not story_ring_elements:
            self.logger.info("No story rings found on the home feed (or selector failed).")
            return
            
        self.logger.info(f"Found {len(story_ring_elements)} story rings on feed. Will attempt to view some.")

        for ring_element in story_ring_elements:
            if self._is_action_blocked_or_limit_reached("story_view"):
                self.logger.info("Stopping feed story viewing due to block or limit.")
                break 

            # TODO: Extract username from story ring element if possible for blacklist check
            # This often involves inspecting child elements or aria-labels which can be fragile.
            # For now, we'll view without pre-blacklist check for simplicity.
            story_owner_username = "FeedUser" # Placeholder
            try: # Try to get username from aria-label of a child or parent if structure allows
                # This is highly speculative and needs inspection
                aria_label_element = ring_element.find_element(By.XPATH, ".//ancestor::div[@role='button' and @aria-label]")
                full_label = aria_label_element.get_attribute("aria-label")
                if "Story by" in full_label: story_owner_username = full_label.split("Story by")[-1].split(",")[0].strip()
            except: pass


            if self.bot.view_story_from_ring(ring_element, story_owner_username):
                self.action_counts["story_views"] += 1
                stories_viewed_this_action += 1
                human_delay("default") # Small delay before trying next story ring
            else:
                self.logger.warning(f"Failed to view story for {story_owner_username} or issue with the ring. May stop trying feed stories.")
                # If one fails, others might too if it's a page structure issue.
                # Consider breaking here or trying only a couple more.
                break 
        
        self.logger.info(f"Viewed {stories_viewed_this_action} stories from feed in this action.")


    def engage_with_user_followers(self, target_usernames_str, engagement_mode="like"):
        if not self.is_pro:
            self.logger.warning("Engaging with user followers is a PRO feature. Please upgrade for access.")
            return
        if not self.bot or not self.bot.driver:
            self.logger.error("Bot not properly initialized. Cannot engage with user followers.")
            return

        target_users = get_list_from_config_string(target_usernames_str)
        if not target_users:
            self.logger.warning("No valid target users provided for follower engagement.")
            return

        self.logger.info(f"[PRO] Starting follower engagement (mode: {engagement_mode}) for users: {', '.join(target_users)}")

        for i, target_user_main in enumerate(target_users):
            if self.action_counts["targets_processed"] >= self.current_run_limits['max_targets']:
                self.logger.info(f"Max target limit ({self.current_run_limits['max_targets']}) reached for PRO. Stopping follower processing.")
                break
            
            self.logger.info(f"--- Processing followers of target user: {target_user_main} ({i+1}/{len(target_users)}) ---")
            if not self.bot.navigate_to_url(f"/{target_user_main.strip()}/"):
                self.logger.warning(f"Failed to navigate to profile of {target_user_main}. Skipping.")
                continue
            
            self.action_counts["targets_processed"] += 1
            human_delay("navigation")

            # Click followers button
            if not self.bot._click_element("profile_page.followers_button_link", f"Followers button for {target_user_main}"):
                self.logger.warning(f"Could not click followers button for {target_user_main}. Skipping.")
                continue
            
            human_delay("navigation") # Wait for followers dialog to load

            # Wait for the dialog itself
            followers_dialog = self.bot._find_element("profile_page.followers_dialog", timeout_override=10)
            if not followers_dialog:
                self.logger.warning(f"Followers dialog for {target_user_main} did not appear. Skipping.")
                take_screenshot(self.bot.driver, f"no_followers_dialog_{target_user_main}")
                # Try to close any potential stuck overlay by navigating away
                self.bot.navigate_to_url("/")
                continue

            self.logger.info(f"Followers dialog opened for {target_user_main}. Scraping followers...")
            
            # Scroll and scrape followers (this is a simplified scroll)
            # Real scrolling needs to handle dynamic loading and end conditions.
            collected_follower_usernames = set()
            SCROLL_ATTEMPTS = 5 # Limit scrolls to avoid getting stuck
            MAX_FOLLOWERS_TO_GET_PER_TARGET = self.config.getint('ProSettings', 'max_followers_to_get_per_target', fallback=20) # Example config

            # Get the scrollable element within the dialog (often the <ul> or a parent div)
            # This selector is tricky: it might be the dialog itself or a child.
            # For now, let's assume the dialog is scrollable or a main list inside it.
            # A common pattern is a div with style overflow-y: scroll.
            # Example: scrollable_list_in_dialog = self.bot._find_element(XPATH, ".//div[@style='overflow-y: scroll;']", parent_element=followers_dialog)
            # If specific scrollable element not found, try scrolling the dialog itself (less reliable)
            scroll_target_for_keys = followers_dialog 

            last_height = self.bot.driver.execute_script("return arguments[0].scrollHeight", scroll_target_for_keys)

            for scroll_attempt in range(SCROLL_ATTEMPTS):
                if len(collected_follower_usernames) >= MAX_FOLLOWERS_TO_GET_PER_TARGET: break

                follower_list_items = self.bot._find_elements("profile_page.followers_list_in_dialog", parent_element=followers_dialog)
                if not follower_list_items and scroll_attempt == 0: # No items on first load
                    self.logger.warning("No follower list items found in dialog initially.")
                    break

                for item_el in follower_list_items:
                    if len(collected_follower_usernames) >= MAX_FOLLOWERS_TO_GET_PER_TARGET: break
                    try:
                        # Selector for username must be relative to item_el
                        username_el = self.bot._find_element("profile_page.follower_username_link_in_list_item", parent_element=item_el, timeout_override=1)
                        if username_el and username_el.text:
                            follower_username = username_el.text.strip()
                            if follower_username: collected_follower_usernames.add(follower_username)
                    except Exception: # Catch all for finding username in list item
                        pass # Silently skip if username not found in an item

                self.logger.debug(f"Scroll attempt {scroll_attempt+1}: Collected {len(collected_follower_usernames)} unique follower usernames so far.")
                
                # Scroll down
                self.bot.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_target_for_keys)
                human_delay("navigation", min_override=1, max_override=2) # Wait for new content to load
                
                new_height = self.bot.driver.execute_script("return arguments[0].scrollHeight", scroll_target_for_keys)
                if new_height == last_height and scroll_attempt > 0: # No more new content
                    self.logger.info("Reached end of followers list (no new content after scroll).")
                    break
                last_height = new_height

            self.logger.info(f"Scraped {len(collected_follower_usernames)} followers for {target_user_main}.")

            # Close followers dialog (Escape key is often most reliable)
            self.bot.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            human_delay("navigation")

            # Now iterate through collected_follower_usernames and engage
            for follower_idx, follower_name in enumerate(list(collected_follower_usernames)): # Convert set to list
                self.logger.info(f"-- Engaging with follower {follower_idx+1}/{len(collected_follower_usernames)}: {follower_name} --")
                if self._is_target_blacklisted(follower_name): continue

                if not self.bot.navigate_to_url(f"/{follower_name}/"):
                    self.logger.warning(f"Failed to navigate to {follower_name}'s profile. Skipping.")
                    continue
                human_delay("navigation")

                # Perform action based on engagement_mode
                if engagement_mode in ["like", "both"]:
                    if self._is_action_blocked_or_limit_reached("like"):
                        self.logger.info(f"Stopping 'like' actions for followers of {target_user_main} due to block or limit.")
                        break # Break from processing this target user's followers
                    
                    # Like 1-2 recent posts on follower's profile (requires selectors for profile grid posts)
                    # This is similar to hashtag liking: find thumbnail, click, like in modal, close modal
                    self.logger.info(f"Attempting to like recent post(s) of {follower_name} (Placeholder logic).")
                    # Example: Find first post thumbnail on profile
                    # profile_post_thumb = self.bot._find_element("profile_page.first_post_thumbnail", timeout_override=5) # Needs this selector
                    # if profile_post_thumb and self.bot._click_element(profile_post_thumb, "..."):
                    #    if self.bot.like_post_in_modal(): self.action_counts["likes"] += 1
                    #    self.bot.close_post_modal()

                if engagement_mode in ["story_view", "both"]:
                    if self._is_action_blocked_or_limit_reached("story_view"):
                        self.logger.info(f"Stopping 'story_view' actions for followers of {target_user_main} due to block or limit.")
                        break
                    # Check for story ring on follower's profile page and view if present
                    # (Needs selector for story ring on a profile page, if different from feed)
                    # profile_story_ring = self.bot._find_element("profile_page.story_ring_indicator", timeout_override=3)
                    # if profile_story_ring and self.bot.view_story_from_ring(profile_story_ring, follower_name):
                    #    self.action_counts["story_views"] += 1
                    self.logger.info(f"Attempting to view story of {follower_name} (Placeholder logic).")
                
                if (self.action_counts["likes"] >= self.current_run_limits['max_likes'] and
                    self.action_counts["story_views"] >= self.current_run_limits['max_story_views']):
                    self.logger.info("All primary action limits reached during follower engagement.")
                    return # Exit follower engagement entirely if global limits hit

                human_delay("default", min_override=4, max_override=8) # Delay between engaging different followers

            if (self.action_counts["likes"] >= self.current_run_limits['max_likes'] and
                self.action_counts["story_views"] >= self.current_run_limits['max_story_views']):
                return # Exit if limits hit

            human_delay("navigation", min_override=10, max_override=20) # Longer delay between processing different target users


    def print_summary(self):
        self.logger.info("--- Engagement Run Summary ---")
        self.logger.info(f"Targets Processed: {self.action_counts['targets_processed']}/{self.current_run_limits['max_targets']}")
        self.logger.info(f"Posts Liked: {self.action_counts['likes']}/{self.current_run_limits['max_likes']}")
        self.logger.info(f"Stories Viewed: {self.action_counts['story_views']}/{self.current_run_limits['max_story_views']}")
        if self.is_warmup_active_for_session:
            self.logger.info(f"(Warmup active for this session - Day {self.current_warmup_day} - limits were adjusted)")
        self.logger.info("------------------------------")
        # TODO: If warmup is active, save the next warmup day for this account.
