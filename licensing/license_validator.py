# Using bot.utils to ensure consistent logger and config access
# Adjust path if utils is not directly accessible or structure changes
import os, sys
# Correctly find project root to add to sys.path for bot.utils
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot.utils import get_logger, get_config

class LicenseValidator:
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        if not self.config:
            self.logger.error("LicenseValidator: Config not loaded. Cannot get license key.")
            self.license_key_from_config = None
        else:
            self.license_key_from_config = self.config.get('ProSettings', 'license_key', fallback=None)

    def is_pro_license_active(self):
        """
        Validates the Pro license.
        This is a placeholder. Real validation should be against a server
        or use a more secure local mechanism if offline.
        """
        if not self.license_key_from_config or not self.license_key_from_config.strip():
            self.logger.info("No Pro license key found in config or key is empty.")
            return False

        # --- Simple Placeholder Check ---
        # Example: Key must start with "HS-PRO-" and be of a certain length
        # THIS IS NOT SECURE FOR A REAL PRODUCT.
        if self.license_key_from_config.strip().startswith("HS-PRO-") and len(self.license_key_from_config.strip()) > 10:
            self.logger.info(f"Pro license key '{self.license_key_from_config[:15]}...' accepted (placeholder validation).")
            # In a real app, log successful validation to your server if possible
            return True
        else:
            self.logger.warning(f"Pro license key '{self.license_key_from_config}' is invalid based on placeholder validation rules.")
            return False

# Example of how you might fetch machine ID for server-side binding (platform dependent and can be complex)
# import uuid
# def get_machine_id_basic():
#     # MAC address based, not always unique, permissions can be an issue, can be spoofed.
#     # Use with caution and combine with other factors if used for licensing.
#     try:
#         return str(uuid.getnode())
#     except Exception as e:
#         get_logger().warning(f"Could not get basic machine ID (MAC address): {e}")
#         return None
