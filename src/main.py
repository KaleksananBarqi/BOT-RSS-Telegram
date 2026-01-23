import asyncio
import time
import signal
import sys
from config.config import RSS_URLS, DELAY_BETWEEN_POSTS, CHECK_INTERVAL
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
                
                # 1. Fetch Feed
                # print(f"Checking: {url}") # Optional log
                entries = rss_service.fetch_feed(url)
                
                # 2. Filter New Entries
                pass # logic below...

                # Kita balik urutannya agar memproses dari yang paling bawah (terlama) di list feed 
                # ke yang paling atas (terbaru), sehingga urutan posting di Telegram logis kronologis.
                new_entries = []
                for entry in reversed(entries):
                    # Gunakan ID atau Link sebagai identifier unik
                    identifier = entry.get('id', entry.get('link'))
                    if rss_service.is_new(identifier):
                        new_entries.append(entry)

                if new_entries:
                    print(f"[{url}] Found {len(new_entries)} new articles.")
                    
                    for entry in new_entries:
                        if not running: break
                        
                        parsed_data = rss_service.parse_entry(entry)
                        identifier = parsed_data['id']
                        
                        # 3. Send to Telegram
                        success = await bot_service.send_post(parsed_data)
                        
                        if success:
                            # 4. Mark as Read
                            rss_service.mark_as_read(identifier)
                            # 5. Delay per message (Spec #6)
                            await asyncio.sleep(DELAY_BETWEEN_POSTS)
                        else:
                            print(f"Failed to send: {identifier}")
                else:
                    pass
                    # print(f"[{url}] No new articles.")
            
        except Exception as e:
            print(f"An error occurred in main loop: {e}")
            await asyncio.sleep(5)

        # 6. Wait for next check cycle
        if running:
            # print(f"Sleeping for {CHECK_INTERVAL} seconds...") # Optional verbose logging
            # Kita gunakan loop kecil untuk sleep agar responsif terhadap signal stop
            for _ in range(CHECK_INTERVAL):
                if not running: break
                await asyncio.sleep(1)

    print("Bot stopped successfully.")

if __name__ == "__main__":
    asyncio.run(main())
