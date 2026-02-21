import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import aiohttp

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set dummy environment variables to bypass config check
os.environ['BOT_TOKEN'] = 'dummy_token'
os.environ['GROUP_ID'] = 'dummy_group_id'

from src.rss_service import RSSService

class TestRSSServiceFetch(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_db = 'tests/test_fetch.db'
        if os.path.exists(self.test_db):
            try: os.remove(self.test_db)
            except: pass
        self.rss_service = RSSService(db_file=self.test_db)
        await self.rss_service.initialize()

    async def asyncTearDown(self):
        if hasattr(self, 'rss_service'):
            await self.rss_service.close()

        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass

    @patch('src.rss_service.feedparser.parse')
    async def test_fetch_feed_success(self, mock_parse):
        # Setup mocks
        url = "http://example.com"
        mock_content = b"feed content"
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = mock_content

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.get.return_value = mock_context
        mock_session.closed = False
        
        self.rss_service.session = mock_session

        # Mock feedparser result
        mock_feed = MagicMock()
        mock_feed.entries = [{'title': 'Test Entry'}]
        mock_feed.bozo = False
        mock_parse.return_value = mock_feed

        entries = await self.rss_service.fetch_feed(url)

        # Verify
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['title'], 'Test Entry')
        mock_parse.assert_called_once_with(mock_content)

    @patch('src.rss_service.feedparser.parse')
    async def test_fetch_feed_fallback(self, mock_parse):
        # Setup mocks to fail aiohttp request
        url = "http://example.com"
        mock_content = b"fallback content"
        
        mock_context = AsyncMock()
        mock_context.__aenter__.side_effect = Exception("Network Error")

        mock_session = MagicMock()
        mock_session.get.return_value = mock_context
        mock_session.closed = False
        self.rss_service.session = mock_session

        # Mock feedparser result for fallback
        mock_feed = MagicMock()
        mock_feed.entries = [{'title': 'Fallback Entry'}]
        mock_feed.bozo = False
        mock_parse.return_value = mock_feed

        # Mock _fetch_feed_blocking
        with patch.object(self.rss_service, '_fetch_feed_blocking', return_value=mock_content) as mock_blocking:
            entries = await self.rss_service.fetch_feed(url)

            # Verify
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['title'], 'Fallback Entry')
            mock_blocking.assert_called_with(url)
            mock_parse.assert_called_with(mock_content)

if __name__ == '__main__':
    unittest.main()
