import unittest
from datetime import datetime, timedelta
import sys
import os
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestMainUtils(unittest.TestCase):
    def setUp(self):
        # We need to import calculate_wait_seconds from src.main
        # But src.main imports config, which executes load_dotenv() and checks env vars.
        # We want to bypass config execution to avoid needing .env file.

        # Create a mock config module
        self.mock_config = MagicMock()
        self.mock_config.RSS_URLS = []
        self.mock_config.DELAY_BETWEEN_POSTS = 1
        self.mock_config.CHECK_INTERVAL_HOURS = 1
        self.mock_config.MAX_NEWS_AGE_HOURS = 1

        # Patch sys.modules to return our mock for 'config' and 'config.config'
        self.modules_patcher = patch.dict(sys.modules, {
            'config': self.mock_config,
            'config.config': self.mock_config
        })
        self.modules_patcher.start()

        # Ensure src.main is reloaded to use the mocked config
        if 'src.main' in sys.modules:
            del sys.modules['src.main']

        # Also need to clear src.rss_service and src.bot_service if they were imported,
        # so they re-import config (getting our mock)
        if 'src.rss_service' in sys.modules:
            del sys.modules['src.rss_service']
        if 'src.bot_service' in sys.modules:
            del sys.modules['src.bot_service']

        # Now import src.main
        # Note: src.rss_service imports sqlite3, etc. Should be fine.
        # src.bot_service imports telegram. Should be fine.

        try:
            from src.main import calculate_wait_seconds
            self.calculate_wait_seconds = calculate_wait_seconds
        except Exception as e:
            self.fail(f"Failed to import src.main: {e}")

    def tearDown(self):
        self.modules_patcher.stop()

    def test_calculate_wait_seconds_1_hour_interval(self):
        # 13:15, interval 1 -> target 14:00 -> wait 45 mins = 2700 sec
        now = datetime(2023, 1, 1, 13, 15, 0)
        interval = 1
        wait = self.calculate_wait_seconds(now, interval)
        self.assertEqual(wait, 2700)

    def test_calculate_wait_seconds_2_hour_interval_odd_hour(self):
        # 13:15, interval 2 -> 13%2=1 -> add 1 -> target 14:00 -> wait 45 mins = 2700 sec
        now = datetime(2023, 1, 1, 13, 15, 0)
        interval = 2
        wait = self.calculate_wait_seconds(now, interval)
        self.assertEqual(wait, 2700)

    def test_calculate_wait_seconds_2_hour_interval_even_hour(self):
        # 12:15, interval 2 -> 12%2=0 -> add 2 -> target 14:00 -> wait 1h 45m = 6300 sec
        now = datetime(2023, 1, 1, 12, 15, 0)
        interval = 2
        wait = self.calculate_wait_seconds(now, interval)
        self.assertEqual(wait, 6300)

    def test_calculate_wait_seconds_exact_hour(self):
        # 13:00, interval 1 -> 13%1=0 -> add 1 -> target 14:00 -> wait 3600 sec
        now = datetime(2023, 1, 1, 13, 0, 0)
        interval = 1
        wait = self.calculate_wait_seconds(now, interval)
        self.assertEqual(wait, 3600)

if __name__ == '__main__':
    unittest.main()
