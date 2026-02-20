import unittest
import os
import sys
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import aiohttp # Need to import aiohttp to mock exceptions properly

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock environment variables for config
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['GROUP_ID'] = 'test_group'

from src.rss_service import RSSService

class TestRSSServiceAsync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use a temporary DB file for testing
        self.test_db = 'tests/test_bot_async.db'
        self.test_json = 'tests/test_history_async.json'

        # Ensure clean state
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass
        if os.path.exists(self.test_json):
            try:
                os.remove(self.test_json)
            except OSError:
                pass

        self.rss_service = RSSService(db_file=self.test_db, json_history_file=self.test_json)

    async def asyncTearDown(self):
        # Cleanup
        if hasattr(self, 'rss_service'):
            await self.rss_service.close()

        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass
        if os.path.exists(self.test_json):
            try:
                os.remove(self.test_json)
            except OSError:
                pass

    async def test_fetch_feed_success(self):
        """Test successful feed fetching and parsing."""
        url = "http://example.com/rss"
        mock_content = b"<rss>...</rss>"
        mock_feed_data = MagicMock()
        mock_feed_data.entries = [{'title': 'Test Entry'}]
        mock_feed_data.bozo = False

        # Mock response context manager
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = mock_content

        # Mock session.get context manager
        mock_session_get = AsyncMock()
        mock_session_get.__aenter__.return_value = mock_response
        mock_session_get.__aexit__.return_value = None

        # Mock session
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        mock_session.get.return_value = mock_session_get

        # Inject mock session into service
        self.rss_service.session = mock_session

        # Mock feedparser.parse
        with patch('src.rss_service.feedparser.parse', return_value=mock_feed_data) as mock_parse:
            entries = await self.rss_service.fetch_feed(url)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['title'], 'Test Entry')
            mock_session.get.assert_called_once()
            mock_parse.assert_called_once_with(mock_content)

    async def test_fetch_feed_http_403(self):
        """Test handling of HTTP 403 Forbidden."""
        url = "http://example.com/rss"

        mock_response = AsyncMock()
        mock_response.status = 403

        mock_session_get = AsyncMock()
        mock_session_get.__aenter__.return_value = mock_response
        mock_session_get.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        mock_session.get.return_value = mock_session_get
        self.rss_service.session = mock_session

        entries = await self.rss_service.fetch_feed(url)
        self.assertEqual(entries, [])

    async def test_fetch_feed_http_error(self):
        """Test handling of other HTTP errors (e.g. 500)."""
        url = "http://example.com/rss"

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session_get = AsyncMock()
        mock_session_get.__aenter__.return_value = mock_response
        mock_session_get.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        mock_session.get.return_value = mock_session_get
        self.rss_service.session = mock_session

        entries = await self.rss_service.fetch_feed(url)
        self.assertEqual(entries, [])

    async def test_fetch_feed_exception_fallback(self):
        """Test fallback to feedparser when aiohttp fails."""
        url = "http://example.com/rss"
        mock_feed_data = MagicMock()
        mock_feed_data.entries = [{'title': 'Fallback Entry'}]
        mock_feed_data.bozo = False

        # Mock session.get raising exception
        mock_session_get = AsyncMock()
        mock_session_get.__aenter__.side_effect = aiohttp.ClientError("Connection Error")

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        mock_session.get.return_value = mock_session_get
        self.rss_service.session = mock_session

        # Mock feedparser.parse for fallback
        # In fallback, feedparser.parse is called with the URL, not content
        with patch('src.rss_service.feedparser.parse', return_value=mock_feed_data) as mock_parse:
            entries = await self.rss_service.fetch_feed(url)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['title'], 'Fallback Entry')

            # Verify fallback call
            # The fallback runs feedparser.parse(url) via run_in_executor
            # Since we patch feedparser.parse, it should be called with url
            mock_parse.assert_called_with(url)

    async def test_fetch_feed_fallback_failure(self):
        """Test failure of both aiohttp and fallback."""
        url = "http://example.com/rss"

        # Mock session.get raising exception
        mock_session_get = AsyncMock()
        mock_session_get.__aenter__.side_effect = aiohttp.ClientError("Connection Error")

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        mock_session.get.return_value = mock_session_get
        self.rss_service.session = mock_session

        # Mock feedparser.parse raising exception
        with patch('src.rss_service.feedparser.parse', side_effect=Exception("Fallback Failed")):
            entries = await self.rss_service.fetch_feed(url)
            self.assertEqual(entries, [])

if __name__ == '__main__':
    unittest.main()
