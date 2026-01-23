import os
import sys
from dotenv import load_dotenv

# ==========================================
# User Configuration
# ==========================================

# RSS Feed URLs
RSS_URLS = [
    'https://pintu.co.id/news/categories/analisis-pasar/rss-feed.xml',
    'https://cryptoharian.com/feed/',
    'https://www.crisisgroup.org/rss',
    'https://decrypt.co/feed',
    'https://id.beincrypto.com/feed/',
    'https://www.investing.com/rss/news_287.rss',
]

# Delay between posts (seconds)
DELAY_BETWEEN_POSTS = 2

# Check interval (hours)
CHECK_INTERVAL_HOURS = 1

# Instant View RHASH (Optional)
IV_RHASH = ''

# Max age of news to process (hours)
MAX_NEWS_AGE_HOURS = 12

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

print("Configuration loaded successfully.")
