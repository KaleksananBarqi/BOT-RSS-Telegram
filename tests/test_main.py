import unittest
import asyncio
import signal
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Set dummy environment variables to pass config check
# This must be done before importing src.main because config is imported at module level
if 'BOT_TOKEN' not in os.environ:
    os.environ['BOT_TOKEN'] = 'dummy_token'
if 'GROUP_ID' not in os.environ:
    os.environ['GROUP_ID'] = 'dummy_group_id'

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import src.main

class TestRSSBot(unittest.TestCase):
    def test_rss_bot_structure(self):
        """
        This test verifies that the RSSBot class exists and has the expected methods.
        """
        # Check if RSSBot class exists in src.main
        self.assertTrue(hasattr(src.main, 'RSSBot'), "RSSBot class not found in src.main")

        # Instantiate RSSBot
        bot = src.main.RSSBot()

        # Check for expected attributes
        self.assertTrue(hasattr(bot, 'running'), "RSSBot should have 'running' attribute")
        self.assertTrue(bot.running, "'running' should be True initially")
        
        # Check for stop_event attribute
        self.assertTrue(hasattr(bot, 'stop_event'), "RSSBot should have 'stop_event' attribute")

        # Check for expected methods
        self.assertTrue(hasattr(bot, 'stop'), "RSSBot should have 'stop' method")
        self.assertTrue(hasattr(bot, 'run'), "RSSBot should have 'run' method")

        # Test stop method
        bot.stop()
        self.assertFalse(bot.running, "'running' should be False after calling stop()")
        self.assertTrue(bot.stop_event.is_set(), "'stop_event' should be set after calling stop()")

if __name__ == '__main__':
    unittest.main()
