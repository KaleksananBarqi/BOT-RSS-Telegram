import asyncio

import signal
import sys
from config.config import RSS_URLS, DELAY_BETWEEN_POSTS, CHECK_INTERVAL, MAX_NEWS_AGE_HOURS
from src.rss_service import RSSService
from src.bot_service import BotService


# Global flag untuk graceful shutdown
running = True

def signal_handler(sig, frame):
    global running
    print("\nStopping bot...")
    running = False

async def main():
    # Setup Signal Handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Bot RSS Telegram Starting...")
    
    rss_service = RSSService()
    bot_service = BotService()

    print(f"Monitoring {len(RSS_URLS)} Feeds...")
    print("Press Ctrl+C to stop.")

    while running:
        try:
            for url in RSS_URLS:
                if not running: break
                
                # Fetch feed
                entries = rss_service.fetch_feed(url)
                
                # Filter by age
                entries = rss_service.filter_entries_by_age(entries, MAX_NEWS_AGE_HOURS)

                # Process entries from oldest to newest
                new_entries = []
                for entry in reversed(entries):
                    identifier = entry.get('id', entry.get('link'))
                    if rss_service.is_new(identifier):
                        new_entries.append(entry)

                if new_entries:
                    print(f"[{url}] Found {len(new_entries)} new articles.")
                    
                    for entry in new_entries:
                        if not running: break
                        
                        parsed_data = rss_service.parse_entry(entry)
                        identifier = parsed_data['id']
                        
                        # Send to Telegram
                        success = await bot_service.send_post(parsed_data)
                        
                        if success:
                            rss_service.mark_as_read(identifier)
                            await asyncio.sleep(DELAY_BETWEEN_POSTS)
                        else:
                            print(f"Failed to send: {identifier}")
                else:
                    pass
            
        except Exception as e:
            print(f"An error occurred in main loop: {e}")
            await asyncio.sleep(5)

        # Wait for next check cycle
        if running:
            for _ in range(CHECK_INTERVAL):
                if not running: break
                await asyncio.sleep(1)

    print("Bot stopped successfully.")

if __name__ == "__main__":
    asyncio.run(main())
