import os
import sys
import json
from dotenv import load_dotenv

# ==========================================
# User Configuration
# ==========================================

# RSS Feed URLs
def load_rss_urls():
    json_path = os.path.join(os.path.dirname(__file__), 'rss_feeds.json')
    if not os.path.exists(json_path):
        print(f"Warning: RSS configuration file not found at {json_path}")
        return []
    try:
        with open(json_path, 'r') as f:
            urls = json.load(f)
            if isinstance(urls, list):
                return urls
            else:
                print(f"Error: Invalid format in {json_path}. Expected a list of URLs.")
                return []
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse {json_path}: {e}")
        return []
    except Exception as e:
        print(f"Error loading RSS URLs: {e}")
        return []

RSS_URLS = load_rss_urls()

# Delay between posts (seconds)
DELAY_BETWEEN_POSTS = 2

# Check interval (hours)
CHECK_INTERVAL_HOURS = 1

# Instant View RHASH (Optional)
IV_RHASH = ''

# Max age of news to process (hours)
MAX_NEWS_AGE_HOURS = 1

# ==========================================
# System Configuration
# ==========================================

# Load environment variables from .env file
load_dotenv()

def get_env_variable(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        print(f"Error: Variable '{name}' is missing in .env file.")
        sys.exit(1)
    return value

# Bot Credentials
BOT_TOKEN = get_env_variable("BOT_TOKEN", required=True)
GROUP_ID = get_env_variable("GROUP_ID", required=True)
TOPIC_ID = get_env_variable("TOPIC_ID") # Optional

# User Agent for HTTP requests
USER_AGENT = get_env_variable("USER_AGENT", default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

print("Configuration loaded successfully.")
