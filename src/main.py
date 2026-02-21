import asyncio
import logging
from datetime import datetime, timedelta

import signal
import sys
from config import RSS_URLS, DELAY_BETWEEN_POSTS, CHECK_INTERVAL_HOURS, MAX_NEWS_AGE_HOURS
from src.rss_service import RSSService
from src.bot_service import BotService

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global flag untuk graceful shutdown
running = True

def signal_handler(sig, frame):
    global running
    logger.info("Stopping bot...")
    running = False

async def main():
    # Setup Signal Handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Bot RSS Telegram Starting...")
    
    rss_service = RSSService()
    await rss_service.init()
    bot_service = BotService()

    logger.info(f"Monitoring {len(RSS_URLS)} Feeds...")
    logger.info("Press Ctrl+C to stop.")

    try:
        while running:
            try:
                for url in RSS_URLS:
                    if not running: break

                    # Fetch feed
                    entries = await rss_service.fetch_feed(url)

                    # Filter by age
                    entries = rss_service.filter_entries_by_age(entries, MAX_NEWS_AGE_HOURS)

                    # Process entries from oldest to newest
                    new_entries = await rss_service.get_new_entries(reversed(entries))

                    if new_entries:
                        logger.info(f"[{url}] Found {len(new_entries)} new articles.")
                        
                        for entry in new_entries:
                            if not running: break

                            parsed_data = rss_service.parse_entry(entry)
                            identifier = parsed_data['id']

                            # Send to Telegram
                            success = await bot_service.send_post(parsed_data)

                            if success:
                                await rss_service.mark_as_read(identifier)
                                await asyncio.sleep(DELAY_BETWEEN_POSTS)
                            else:
                                logger.error(f"Failed to send: {identifier}")
                    else:
                        pass
            
            except Exception as e:
                logger.error(f"An error occurred in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)

            # Wait for next check cycle
            if running:
                now = datetime.now()
                # Hitung waktu target berikutnya (round up ke jam terdekat sesuai interval)
                # Contoh: Interval 1 jam, sekarang 13:15 -> Target 14:00
                # Contoh: Interval 2 jam, sekarang 13:15 -> Target 14:00 (13 ganjil, next genap)

                # Logic: Cari "base hour" saat ini, tambah selisih untuk mencapai kelipatan interval berikutnya
                hours_to_add = CHECK_INTERVAL_HOURS - (now.hour % CHECK_INTERVAL_HOURS)

                # Reset menit/detik ke 0 untuk dapat jam "teng"
                current_hour_floor = now.replace(minute=0, second=0, microsecond=0)
                target_time = current_hour_floor + timedelta(hours=hours_to_add)

                wait_seconds = (target_time - now).total_seconds()

                # Safety buffer jika kalkulasi aneh (negatif atau 0), minimal 1 detik
                if wait_seconds <= 0:
                    wait_seconds = 1

                logger.info(f"Menunggu {int(wait_seconds // 60)} menit dan {int(wait_seconds % 60)} detik hingga pukul {target_time.strftime('%H:%M')}...")

                # Wait loop dengan interrupt check
                # Kita loop per 1 detik agar bisa di-break (Ctrl+C)
                end_time = datetime.now().timestamp() + wait_seconds
                while running and datetime.now().timestamp() < end_time:
                    await asyncio.sleep(1)
    finally:
        await rss_service.close()

    logger.info("Bot stopped successfully.")

if __name__ == "__main__":
    asyncio.run(main())
