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

        # Check for expected methods
        self.assertTrue(hasattr(bot, 'stop'), "RSSBot should have 'stop' method")
        self.assertTrue(hasattr(bot, 'run'), "RSSBot should have 'run' method")

        # Test stop method
        bot.stop()
        self.assertFalse(bot.running, "'running' should be False after calling stop()")

class TestRSSBotAsync(unittest.IsolatedAsyncioTestCase):
    @patch('src.main.RSSService')
    @patch('src.main.BotService')
    @patch('src.main.asyncio.sleep', new_callable=AsyncMock)
    async def test_rss_bot_run_loop(self, mock_sleep, mock_bot_service, mock_rss_service):
        """
        Test the run loop of RSSBot.
        """
        bot = src.main.RSSBot()

        # Mock dependencies
        mock_rss_instance = mock_rss_service.return_value
        # mock_bot_service is not used directly but BotService() is called

        # Setup mocks
        mock_rss_instance.fetch_feed = AsyncMock(return_value=[])
        mock_rss_instance.close = AsyncMock()

        # Stop the bot immediately when sleep is called to avoid infinite loop
        # The main loop calls sleep at the end of the iteration
        async def side_effect(*args, **kwargs):
            bot.stop()

        mock_sleep.side_effect = side_effect

        # Run the bot
        # It should run one iteration then hit sleep, which stops it.
        await bot.run()

        # Verify interactions
        self.assertTrue(mock_rss_instance.fetch_feed.called)
        self.assertTrue(mock_rss_instance.close.called)
        self.assertFalse(bot.running)

if __name__ == '__main__':
    unittest.main()
