import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_env_variable(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        print(f"Error: Variable '{name}' is missing in .env file.")
        sys.exit(1)
    return value

# ==========================================
# User Configuration
# ==========================================

# RSS Feed URLs
# Parse comma-separated list of URLs from environment variable
_rss_urls_env = get_env_variable("RSS_URLS", default="")
RSS_URLS = [url.strip() for url in _rss_urls_env.split(",") if url.strip()]

if not RSS_URLS:
    print("Warning: RSS_URLS environment variable is empty. No feeds will be monitored.")

# Delay between posts (seconds)
DELAY_BETWEEN_POSTS = int(get_env_variable("DELAY_BETWEEN_POSTS", default="2"))

# Check interval (hours)
CHECK_INTERVAL_HOURS = int(get_env_variable("CHECK_INTERVAL_HOURS", default="1"))

# Instant View RHASH (Optional)
IV_RHASH = get_env_variable("IV_RHASH", default="")

# Max age of news to process (hours)
MAX_NEWS_AGE_HOURS = int(get_env_variable("MAX_NEWS_AGE_HOURS", default="1"))

# ==========================================
# System Configuration
# ==========================================

# Bot Credentials
BOT_TOKEN = get_env_variable("BOT_TOKEN", required=True)
GROUP_ID = get_env_variable("GROUP_ID", required=True)
TOPIC_ID = get_env_variable("TOPIC_ID") # Optional

# User Agent for HTTP requests
USER_AGENT = get_env_variable("USER_AGENT", default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

print("Configuration loaded successfully.")
