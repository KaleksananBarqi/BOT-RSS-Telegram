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

class RSSBot:
    def __init__(self):
        self.running = True
        self.rss_service = None
        self.bot_service = None

    def stop(self, *args):
        logger.info("Stopping bot...")
        self.running = False

    async def run(self):
        # Setup Signal Handler
        try:
            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)
        except ValueError:
            # Signals only work in main thread
            pass

        logger.info("Bot RSS Telegram Starting...")

        self.rss_service = RSSService()
        self.bot_service = BotService()

        logger.info(f"Monitoring {len(RSS_URLS)} Feeds...")
        logger.info("Press Ctrl+C to stop.")

        try:
            while self.running:
                try:
                    for url in RSS_URLS:
                        if not self.running: break

                        # Fetch feed
                        entries = await self.rss_service.fetch_feed(url)

                        # Filter by age
                        entries = self.rss_service.filter_entries_by_age(entries, MAX_NEWS_AGE_HOURS)

                        # Process entries from oldest to newest
                        new_entries = self.rss_service.get_new_entries(reversed(entries))

                        if new_entries:
                            logger.info(f"[{url}] Found {len(new_entries)} new articles.")

                            for entry in new_entries:
                                if not self.running: break

                                parsed_data = self.rss_service.parse_entry(entry)
                                identifier = parsed_data['id']

                                # Send to Telegram
                                success = await self.bot_service.send_post(parsed_data)

                                if success:
                                    self.rss_service.mark_as_read(identifier)
                                    await asyncio.sleep(DELAY_BETWEEN_POSTS)
                                else:
                                    logger.error(f"Failed to send: {identifier}")
                        else:
                            pass

                except Exception as e:
                    logger.error(f"An error occurred in main loop: {e}", exc_info=True)
                    await asyncio.sleep(5)

                # Wait for next check cycle
                if self.running:
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
                    while self.running and datetime.now().timestamp() < end_time:
                        await asyncio.sleep(1)
        finally:
            if self.rss_service:
                await self.rss_service.close()

        logger.info("Bot stopped successfully.")

async def process_feed(url, rss_service, bot_service):
    """Processes a single RSS feed."""
    # Fetch feed
    entries = await rss_service.fetch_feed(url)

    # Filter by age
    entries = rss_service.filter_entries_by_age(entries, MAX_NEWS_AGE_HOURS)

    # Process entries from oldest to newest
    new_entries = rss_service.get_new_entries(reversed(entries))

    if new_entries:
        logger.info(f"[{url}] Found {len(new_entries)} new articles.")

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
                logger.error(f"Failed to send: {identifier}")

async def wait_until_next_run(wait_seconds):
    """Waits for the specified duration, checking running flag."""
    target_time = datetime.now() + timedelta(seconds=wait_seconds)
    logger.info(f"Menunggu {int(wait_seconds // 60)} menit dan {int(wait_seconds % 60)} detik hingga pukul {target_time.strftime('%H:%M')}...")

    end_time = datetime.now().timestamp() + wait_seconds
    while running and datetime.now().timestamp() < end_time:
        await asyncio.sleep(1)

def calculate_wait_seconds(now, interval_hours):
    """Calculates wait time until next scheduled run."""
    # Hitung waktu target berikutnya (round up ke jam terdekat sesuai interval)
    # Contoh: Interval 1 jam, sekarang 13:15 -> Target 14:00
    # Contoh: Interval 2 jam, sekarang 13:15 -> Target 14:00 (13 ganjil, next genap)

    # Logic: Cari "base hour" saat ini, tambah selisih untuk mencapai kelipatan interval berikutnya
    hours_to_add = interval_hours - (now.hour % interval_hours)

    # Reset menit/detik ke 0 untuk dapat jam "teng"
    current_hour_floor = now.replace(minute=0, second=0, microsecond=0)
    target_time = current_hour_floor + timedelta(hours=hours_to_add)

    wait_seconds = (target_time - now).total_seconds()

    # Safety buffer jika kalkulasi aneh (negatif atau 0), minimal 1 detik
    if wait_seconds <= 0:
        wait_seconds = 1

    return wait_seconds

async def main():
    bot = RSSBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
