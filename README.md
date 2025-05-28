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

## Usage

Run the main script from the root directory of the project (`hsecurities-engagement_booster/`):

```bash
python main.py [OPTIONS]
