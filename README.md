# hSECURITIES Instagram Engagement Booster

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) <!-- Ensure you have a LICENSE file -->
[![Status](https://img.shields.io/badge/status-beta_foundation-orange.svg)]()

**hSECURITIES Engagement Booster** is an advanced command-line tool built with Python and Selenium designed to help automate certain Instagram interactions like targeted liking and story viewing. This tool is provided with a focus on human-like behavior simulation and robust error handling.

**This tool is intended for educational, experimental, and personal use only.**

---

**🚨 CRITICAL WARNING & DISCLAIMER 🚨**

*   **RISK OF ACCOUNT BAN/RESTRICTION:** Automating Instagram actions is **strictly against Instagram's Terms of Service**. Using this tool, or any automation tool, can lead to temporary blocks, shadowbans, feature restrictions, or **permanent suspension** of your Instagram account(s).
*   **USE AT YOUR OWN RISK:** The developers and contributors of hSECURITIES Engagement Booster are **not responsible** for any negative consequences, including account bans or restrictions, that may arise from the use or misuse of this software. You assume all responsibility.
*   **EDUCATIONAL & EXPERIMENTAL PURPOSES:** This tool is provided for educational insight into browser automation, web interaction, and software development. It is not intended for unethical use, spamming, generating inauthentic engagement, or any activities that violate Instagram's policies or applicable laws.
*   **BURNER ACCOUNTS STRONGLY RECOMMENDED:** It is **imperative** to test and use this tool *exclusively* with dedicated **test/burner accounts** that you are willing to lose. **DO NOT use it on your primary, important, or commercial Instagram accounts.**
*   **CONSTANTLY EVOLVING PLATFORM:** Instagram frequently updates its platform, website structure, and anti-automation measures. This can (and will) break automation tools. This tool will require **ongoing maintenance and updates** to its UI selectors (`selectors.yaml`) and interaction logic to remain functional. No guarantees of continued functionality or undetectability are provided.

---

## Key Features

*   **Targeted Engagement:**
    *   Like posts based on specified hashtags.
    *   View stories from your home feed.
    *   (PRO Conceptual) Engage with followers of target users (liking their posts, viewing their stories).
*   **Human-like Behavior Simulation:**
    *   Configurable, randomized delays between actions (navigation, typing, interaction).
    *   Random user-agent rotation from a user-provided list.
    *   Human-like typing simulation for input fields.
    *   (Conceptual) Session warm-up logic for new accounts/sessions.
*   **Robust Configuration:**
    *   Detailed `user_config.ini` file for all operational settings.
    *   **Externalized UI Selectors:** All CSS Selectors and XPaths are managed in `config/selectors.yaml`, making it easier to update them as Instagram's UI changes without modifying Python code.
*   **Session Management:**
    *   Saves and loads browser session cookies to reduce login frequency and appear more natural.
*   **Demo vs. Pro (Conceptual Model):**
    *   **Demo Mode (Free):** The version in this repository operates with limited action quotas and restricted access to advanced features.
    *   **Pro Mode (Conceptual - Support Tier):** A conceptual tier for supporters that would unlock higher limits, advanced targeting options (like `user_followers` engagement), and potentially proxy support.
*   **Logging & Error Handling:**
    *   Detailed activity logging to both console and a file (`logs/activity.log`).
    *   Retry mechanisms for transient Selenium errors.
    *   Automatic screenshot capture on critical errors for easier debugging.
    *   Basic detection of common Instagram action blocks/challenges.

---

## Prerequisites

*   Python 3.8 or higher (Python 3.9+ recommended).
*   Google Chrome browser installed and updated.
*   `pip` (Python package installer).
*   A stable internet connection.

---

## Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/[YOUR_GITHUB_USERNAME_HERE]/hsecurities-engagement-booster.git
    cd hsecurities-engagement-booster
    ```

2.  **Create and activate a virtual environment (highly recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    This installs Selenium, PyYAML, webdriver-manager, etc. `webdriver-manager` will attempt to automatically download the correct ChromeDriver for your installed Chrome version.

4.  **Initial Configuration (Crucial Steps):**

    *   **Copy `config/user_config.ini.template` to `config/user_config.ini`**.
        ```bash
        # On Windows (PowerShell/cmd):
        # copy config\user_config.ini.template config\user_config.ini
        # On macOS/Linux:
        # cp config/user_config.ini.template config/user_config.ini
        ```

    *   **Edit `config/user_config.ini`**:
        *   Set your Instagram `username` under `[Credentials]`.
        *   **Password:** It is **strongly recommended** to leave the `password` field blank in the config file. The script will securely prompt you for it when run (input will not be displayed). Storing passwords in plain text is a security risk.
        *   Review and adjust other settings: `headless_browser`, delays (`AntiDetection` section), action limits (`DemoLimits` or `ProSettings` section).

    *   **Populate `config/user_agents.txt`**:
        *   This file should contain a list of valid browser user-agent strings, one per line.
        *   Search online for "common user agents list" or "my user agent" to find examples. Add at least 10-20 diverse (desktop/mobile) user agents.

    *   **(ONGOING & CRITICAL TASK) Update `config/selectors.yaml`**:
        *   This YAML file stores the UI element selectors (XPaths, CSS Selectors) that the bot uses to find elements on Instagram's website.
        *   **Instagram changes its website structure frequently, which WILL BREAK these selectors.**
        *   You **MUST** use your browser's Developer Tools (right-click on an element -> "Inspect") to find the current, correct, and most robust selectors for each item listed in `selectors.yaml`.
        *   The `selectors.yaml` file provided in this repository contains **EXAMPLES AND PLACEHOLDERS THAT WILL LIKELY NEED IMMEDIATE ADJUSTMENT TO WORK WITH THE CURRENT INSTAGRAM UI.** See the "Maintaining Selectors" section below.

---

**Command-line Arguments (`python main.py --help` for full list):**

*   `--config FILE_PATH`: Path to your configuration file (default: `config/user_config.ini` relative to `main.py`).
*   `--mode MODE`: Specifies the engagement mode.
    *   `like`: Only perform "like" actions.
    *   `story_view`: Only perform "story view" actions.
    *   `both`: Perform both "like" and "story view" actions (default for hashtag/user targets).
    *   `feed_stories`: Specifically view stories from your home feed.
*   `--target-type TYPE`: Defines the source of your engagement targets.
    *   `hashtag`: Engage with content related to specified hashtags (default).
    *   `user_followers`: (PRO Conceptual) Engage with the followers of specified Instagram users.
*   `--targets "TARGET1,TARGET2"`: A comma-separated string of targets (e.g., `"nature,sunset"` for hashtags, or `"userA,userB"` for `user_followers`). **Required if `target-type` is not `feed_stories`.**
*   `--skip-password-prompt`: If the password is not in `user_config.ini`, the script normally prompts for it. Use this flag to disable the prompt (login will fail if the password isn't set).

---

## Pro Version & Monetization (Conceptual Support Tier)

This repository provides a Demo version with limited functionality. The "Pro Version" is currently a **conceptual support tier** for those who wish to encourage further development.

**By supporting the project, you help maintain and improve this tool. As a thank you, supporters may gain access to versions with (conceptually):**

*   **Higher Action Limits:** Increased daily/session quotas for likes, story views, etc.
*   **Advanced Targeting (Conceptual):**
    *   Engage with followers/followings of specific users.
    *   Target users who liked/commented on specific posts.
*   **Proxy Support (Conceptual):** Ability to use your own HTTP/SOCKS5 proxies.

**How to Support and Express Interest in "Pro" Features:**

1.  **Support via PayU (INR):**
    *   **Suggested Support Amount:** **₹99 INR** (One-time)
    *   **Payment Link:** [https://u.payu.in/PAYUMN/2Jn6qaJvdhKD](https://u.payu.in/PAYUMN/2Jn6qaJvdhKD)
    *   **After Supporting:** Please send an email to `[hello@hsecurities.in]` with your PayU transaction ID and the email address where you'd like to receive updates or conceptual Pro version details if/when they become available.

2.  **Support via Bitcoin (BTC):**
    *   **Suggested Support Amount:** Approximately **₹99 INR equivalent in BTC**.
    *   **Current Suggested BTC Amount:** **`[0.000011]`**
    *   **Bitcoin Address:** `1DuVFM8961i8fomMm1sxjJhiCgW6YFA5AH`
    *   **After Supporting:** Please send an email to `[hello@hsecurities.in]` with:
        1.  Your Bitcoin Transaction ID (TXID).
        2.  The approximate BTC amount sent.
        3.  The email address for updates or conceptual Pro version details.
    *   *Note: Bitcoin transactions require network confirmations and include network fees.*

**Important Notes on "Pro" Access (Conceptual):**
*   The current license validation in `licensing/license_validator.py` is a **simple placeholder**. A real Pro version would use a unique license key system.
*   **Delivery & Fulfillment:** As this is a conceptual support tier, please allow up to `[e.g., 24-48 hours]` for manual acknowledgment after sending your support confirmation email. Any "Pro" features or enhanced versions would be communicated via email.
*   **Support Contact:** For any support-related queries, please contact `[YOUR_SUPPORT_EMAIL_ADDRESS_HERE]`.

**Your support helps keep this experimental project alive!**

---

## Maintaining Selectors (`config/selectors.yaml`)

This is the **most critical and frequent maintenance task** for this tool. Instagram's website structure changes often, breaking the bot's ability to find elements.

1.  **Identify a Broken Interaction:** If the bot fails to click a button, find a field, or perform an action, it's likely a selector issue. Check the logs for errors like "Element not found" or "TimeoutException" related to finding an element.
2.  **Open Instagram in your Browser** (preferably in Incognito mode to avoid interference from your own logged-in state or extensions).
3.  **Navigate to the Page/State** where the bot is failing.
4.  **Open Developer Tools:**
    *   Right-click on the specific element the bot needs to interact with (e.g., the "Log In" button, a "Like" icon, a username input field).
    *   Select "Inspect" or "Inspect Element" from the context menu.
5.  **Find a Reliable New Selector in the HTML:**
    *   **Best:** Look for unique `id` attributes.
    *   **Good:** Look for stable and descriptive attributes like `name`, `aria-label`, `role`, `data-testid`.
    *   **Okay (use with caution):** Class names can be used, but Instagram often uses auto-generated or rapidly changing class names. Try to find more unique or stable parts of a class string.
    *   **Construct a CSS Selector or XPath:**
        *   **CSS Selector Example:** `button[data-testid='login_button']`
        *   **XPath Example:** `//button[@type='submit' and .//div[text()='Log In']]`
    *   Test your selector in the Developer Tools console (e.g., using `$x("your_xpath")` for XPaths or `$$("your_css_selector")` for CSS selectors) to ensure it uniquely identifies the correct element.
6.  **Update `config/selectors.yaml`:**
    *   Open `config/selectors.yaml` in a text editor.
    *   Find the entry corresponding to the broken element (e.g., `login_page.login_button`).
    *   Update its `type` (e.g., `XPATH`, `CSS_SELECTOR`) and `value` (the selector string itself) with the new, working selector you found.
7.  **Save `selectors.yaml` and Test the Bot** with the specific action that was failing.

**Tips for Robust Selectors:**
*   Avoid selectors that are very long or rely on deep nesting if possible.
*   Prefer attributes designed for accessibility (`aria-label`, `role`) or testing (`data-testid`) if Instagram uses them, as these tend to be more stable than purely stylistic classes.
*   Be specific enough to target the correct element but general enough not to break with minor text or layout changes.

---

## Troubleshooting Common Issues

*   **"Element not found" / TimeoutException on element find:** This almost always means the corresponding selector in `config/selectors.yaml` is outdated or incorrect for the current Instagram UI. Refer to "Maintaining Selectors" above.
*   **Login Failures:**
    *   Double-check your `username` in `user_config.ini`.
    *   Ensure you are entering the correct password when prompted (or that it's correct in the config, if stored there).
    *   **Instagram Security Checkpoints:** Instagram might be presenting a CAPTCHA, a 2-Factor Authentication (2FA) prompt, a "Suspicious Login Attempt" verification, or asking you to confirm your identity. The bot has very limited (or no) automated handling for these.
        *   **Solution:** Try logging into the account manually using a normal web browser *from the same IP address/machine* the bot is running on. Resolve any security checkpoints presented by Instagram. Then, try running the bot again.
    *   The bot attempts to save and load cookies. If cookies are corrupted or very old, login might fail. Try deleting the `.cookies/` directory (it will be recreated) to force a fresh login.
*   **WebDriverException / ChromeDriver Errors:**
    *   "Cannot find chrome binary": Google Chrome is not installed or not found in the system's PATH.
    *   "This version of ChromeDriver only supports Chrome version X": Your installed Google Chrome browser and the ChromeDriver version are incompatible.
        *   **Solution:**
            1.  Update your Google Chrome browser to the latest version.
            2.  `webdriver-manager` (used by the script) should then download the correct ChromeDriver. If issues persist, you might need to clear `webdriver-manager`'s cache (usually in `~/.wdm/` or `%USERPROFILE%\.wdm\`) or manually specify a ChromeDriver version if `webdriver-manager` struggles.
*   **"Action Blocked" Messages from Instagram:**
    *   If the bot logs indicate "ACTION BLOCKED" or you see this message on the account manually, Instagram has detected suspicious activity.
    *   **Solution:** Stop using the bot **immediately** on that account for several days (e.g., 3-7 days, or even longer). When/if you resume, significantly reduce the action limits in `user_config.ini` and consider using the (conceptual) session warm-up feature. Frequent action blocks can lead to permanent suspension.
*   **ImportError:** Usually means you are not running `python main.py` from the root `hsecurities-engagement-booster/` directory, your virtual environment is not activated, or `requirements.txt` was not installed correctly.

---

## Future Development Ideas (Conceptual)

*   Robust handling of Instagram's security checkpoints (very challenging).
*   Advanced warm-up schedules per account with persistent state.
*   GUI interface (e.g., using Tkinter, PyQt, or a web framework like Flask/Streamlit).
*   Support for more engagement types (e.g., commenting, following - **EXTREMELY HIGH RISK OF ACCOUNT BAN**).
*   Database integration for managing multiple accounts, their states, schedules, and proxies.
*   Full server-side Pro license validation, management, and automated fulfillment.
*   AI-powered comment generation (highly complex, ethically questionable, and still very risky).

---

## Contributing

While this is primarily an experimental project, constructive feedback, bug reports (especially related to selector changes or Instagram's anti-bot measures), and ethical feature suggestions are welcome. Please open an issue on GitHub to discuss potential changes or report problems.

*(You can adjust this section based on your actual willingness to accept external contributions and how you'd like them managed.)*

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
*(Ensure you create a `LICENSE` file in your repository root. The MIT license text can be found at [https://opensource.org/licenses/MIT](https://opensource.org/licenses/MIT))*

---

**Stay Safe, Be Ethical, & Use Responsibly!**
This tool interacts with a live platform. Understanding the risks involved and adhering to Instagram's policies (even while experimenting) is crucial.

## Usage

Run the main script from the root directory of the project (`hsecurities-engagement_booster/`):

```bash
python main.py [OPTIONS]
