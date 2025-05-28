from .utils import get_logger, get_config, get_list_from_config_string
from .anti_detection import human_delay #, get_warmup_action_multiplier, should_perform_warmup

class EngagementActions:
    def __init__(self, bot_instance, is_pro_user):
        self.bot = bot_instance # This is an initialized InstagramBot instance
        self.logger = get_logger()
        self.config = get_config()
        self.is_pro = is_pro_user

        self.current_run_limits = {}
        self.action_counts = {"likes": 0, "story_views": 0, "targets_processed": 0}
        self._load_run_limits()

        self.blacklist_users = get_list_from_config_string(self.config.get('Blacklist', 'users_to_avoid', fallback=''))
        # self.current_warmup_day = 0 # Manage this state if warmup is enabled

    def _load_run_limits(self):
        limit_section = 'ProSettings' if self.is_pro else 'DemoLimits'
        self.current_run_limits['max_likes'] = self.config.getint(limit_section, 'max_likes_per_run', fallback=10)
        self.current_run_limits['max_story_views'] = self.config.getint(limit_section, 'max_story_views_per_run', fallback=15)
        self.current_run_limits['max_targets'] = self.config.getint(limit_section, 'max_targets_per_run', fallback=1)
        
        # Apply warmup multiplier if applicable
        # if should_perform_warmup(self.bot.username):
        #     multiplier = get_warmup_action_multiplier(self.current_warmup_day)
        #     self.current_run_limits['max_likes'] = int(self.current_run_limits['max_likes'] * multiplier)
        #     # ... and for other limits
        #     self.logger.info(f"Warmup active: Action limits adjusted by multiplier {multiplier:.2f}")

    def _check_action_block_and_limits(self, action_type):
        if self.bot.check_for_action_block(): return False # Stop if blocked

        if action_type == "like" and self.action_counts["likes"] >= self.current_run_limits['max_likes']:
            self.logger.info("Like limit reached for this run.")
            return False
        if action_type == "story_view" and self.action_counts["story_views"] >= self.current_run_limits['max_story_views']:
            self.logger.info("Story view limit reached for this run.")
            return False
        return True

    def _is_target_blacklisted(self, username_or_content):
        # Basic user blacklist check
        if username_or_content.lower() in self.blacklist_users:
            self.logger.info(f"Target '{username_or_content}' is blacklisted. Skipping.")
            return True
        # Add keyword blacklist check for bios/captions if implemented (more complex)
        return False

    def engage_with_hashtags(self, hashtags_str, mode="both"):
        if not self.bot or not self.bot.driver: return
        
        hashtags = get_list_from_config_string(hashtags_str)
        if not hashtags:
            self.logger.warning("No hashtags provided for engagement.")
            return

        self.logger.info(f"Starting hashtag engagement (mode: {mode}) for: {', '.join(hashtags)}")

        for i, hashtag in enumerate(hashtags):
            if self.action_counts["targets_processed"] >= self.current_run_limits['max_targets']:
                self.logger.info(f"Max target limit ({self.current_run_limits['max_targets']}) reached.")
                break
            
            self.logger.info(f"Processing hashtag #{hashtag}...")
            if not self.bot.navigate_to_url(f"/explore/tags/{hashtag.strip()}/"):
                continue # Skip if navigation fails

            self.action_counts["targets_processed"] += 1
            human_delay("navigation")

            # Example: Like the first few posts from hashtag (very basic)
            if mode in ["like", "both"]:
                # This needs a robust way to get post elements/links from hashtag page
                # For now, let's assume we get one post link (e.g., the first one)
                # This part is highly dependent on your selectors.yaml for hashtag_page.first_post_thumbnail_link
                first_post_link_element = self.bot._find_element("hashtag_page.first_post_thumbnail_link", timeout=10)
                if first_post_link_element:
                    post_url = first_post_link_element.get_attribute("href")
                    if post_url:
                        self.logger.info(f"Found post to interact with: {post_url}")
                        # Get username from post_url or page if needed for blacklist
                        # For simplicity, skipping advanced blacklist for now.

                        if not self._check_action_block_and_limits("like"): break # Stop all if blocked or limit reached
                        
                        # Click the thumbnail to open modal
                        if self.bot._click_element(first_post_link_element, f"Post thumbnail for {hashtag}"):
                            human_delay("navigation")
                            if self.bot.like_post_in_modal():
                                self.action_counts["likes"] += 1
                            self.bot.close_post_modal() # Ensure modal is closed
                            human_delay("default")
                        else:
                            self.logger.warning(f"Failed to click post thumbnail for #{hashtag}")
                    else:
                        self.logger.warning(f"Could not get URL from first post thumbnail for #{hashtag}")
                else:
                    self.logger.warning(f"No post thumbnails found on hashtag page for #{hashtag} (check selectors).")

            # Placeholder for story viewing by hashtag (complex)
            if mode in ["story_view", "both"]:
                 if not self._check_action_block_and_limits("story_view"): break
                 self.logger.info(f"Story viewing by hashtag '{hashtag}' - (Needs implementation: find users from posts, then view their stories)")
                 # self.action_counts["story_views"] += 1 # Increment if a story is viewed

            if (self.action_counts["likes"] >= self.current_run_limits['max_likes'] and
                self.action_counts["story_views"] >= self.current_run_limits['max_story_views']):
                self.logger.info("All action limits reached.")
                break
            human_delay("session") # Longer delay between processing different hashtags

    def view_feed_stories(self):
        if not self.bot or not self.bot.driver: return
        self.logger.info("Attempting to view stories from home feed.")
        if not self.bot.navigate_to_url("/"): return

        viewed_in_this_session = 0
        max_to_view_now = self.current_run_limits['max_story_views'] - self.action_counts["story_views"]

        if max_to_view_now <= 0:
            self.logger.info("Story view limit already reached.")
            return

        # Find story rings (needs good selector for "story_viewer.story_ring_on_feed")
        # This is simplified; you'd loop through available story rings
        for i in range(max_to_view_now): # Attempt to view up to the remaining limit
            if not self._check_action_block_and_limits("story_view"): break
            
            # The selector "story_viewer.story_ring_on_feed" should ideally get a list
            # and you'd iterate. This example just tries to find one.
            # A better selector might be "story_viewer.all_story_rings_on_feed" returning a list.
            story_ring = self.bot._find_element("story_viewer.story_ring_on_feed", timeout=5) # Finds the first one usually
            if story_ring:
                # Extract username if possible to check blacklist (complex from just a ring)
                if self.bot.view_story_from_ring(story_ring):
                    self.action_counts["story_views"] += 1
                    viewed_in_this_session += 1
                    human_delay("default") # Small delay before trying next story
                else:
                    self.logger.warning("Failed to view a story or no more distinct stories clickable this way.")
                    break # Stop if one fails, as it might be an issue with selectors or no more stories
            else:
                self.logger.info("No more (or no initial) story rings found on feed.")
                break
        self.logger.info(f"Viewed {viewed_in_this_session} stories from feed in this session.")


    def engage_with_user_followers(self, target_usernames_str, mode="like"):
        if not self.is_pro:
            self.logger.warning("Engaging with user followers is a PRO feature. Skipping.")
            return
        # TODO: Implement robust follower scraping and interaction logic
        # 1. Navigate to target_user profile
        # 2. Click followers button (profile_page.followers_button)
        # 3. Scroll through followers list popup (profile_page.followers_list_popup)
        # 4. Extract follower usernames (profile_page.follower_username_in_list)
        # 5. For each follower:
        #    - Check blacklist
        #    - Navigate to their profile
        #    - Perform 'like' or 'story_view' actions based on 'mode'
        #    - Respect action limits and use human_delay
        self.logger.info(f"[PRO FEATURE] Engaging with followers of '{target_usernames_str}' (mode: {mode}) - NOT FULLY IMPLEMENTED.")
        pass


    def print_summary(self):
        self.logger.info("--- Engagement Run Summary ---")
        self.logger.info(f"Targets Processed: {self.action_counts['targets_processed']}/{self.current_run_limits['max_targets']}")
        self.logger.info(f"Posts Liked: {self.action_counts['likes']}/{self.current_run_limits['max_likes']}")
        self.logger.info(f"Stories Viewed: {self.action_counts['story_views']}/{self.current_run_limits['max_story_views']}")
        self.logger.info("------------------------------")
