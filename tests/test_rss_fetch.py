import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Set required environment variables before importing src
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['GROUP_ID'] = 'test_group'

# Add repo root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rss_service import RSSService

class TestRSSServiceFetch(unittest.TestCase):
    def setUp(self):
        self.db_file = 'tests/test_bot.db'
        self.rss_service = RSSService(db_file=self.db_file, json_history_file='data/history_dummy.json')

    def tearDown(self):
        if hasattr(self.rss_service, 'session') and self.rss_service.session and not isinstance(self.rss_service.session, MagicMock):
             asyncio.run(self.rss_service.session.close())
        if hasattr(self.rss_service, 'conn'):
            self.rss_service.conn.close()
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

    async def run_fetch(self):
        mock_session = MagicMock()
        mock_session.closed = False  # Critical: Prevent _get_session from replacing it

        # Setup response context manager
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b'<rss></rss>'
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        mock_session.get.return_value = mock_response

        # Inject mock session
        self.rss_service.session = mock_session

        await self.rss_service.fetch_feed('http://example.com/feed')
        return mock_session

    def test_fetch_feed_aiohttp_ssl_disabled(self):
        """Test that aiohttp request has ssl=False"""
        mock_session = asyncio.run(self.run_fetch())

        # Check calls
        args, kwargs = mock_session.get.call_args

        self.assertIn('ssl', kwargs, "ssl argument missing in aiohttp.get call")
        self.assertFalse(kwargs['ssl'], "ssl argument should be False")

if __name__ == '__main__':
    unittest.main()
