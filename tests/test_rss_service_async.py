import unittest
import os
import sys
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import aiohttp

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock environment variables for config
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['GROUP_ID'] = 'test_group'

from src.rss_service import RSSService

class TestRSSServiceAsync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_db = 'tests/test_bot_async.db'
        self.test_json = 'tests/test_history_async.json'

        if os.path.exists(self.test_db):
            try: os.remove(self.test_db)
            except: pass
        if os.path.exists(self.test_json):
            try: os.remove(self.test_json)
            except: pass

        self.rss_service = RSSService(db_file=self.test_db, json_history_file=self.test_json)
        # Avoid real DB connection in these fetch tests if possible, but initialize is called
        await self.rss_service.initialize()

    async def asyncTearDown(self):
        if hasattr(self, 'rss_service'):
            await self.rss_service.close()

        for ext in ['', '-shm', '-wal']:
            if os.path.exists(self.test_db + ext):
                try: os.remove(self.test_db + ext)
                except: pass
        if os.path.exists(self.test_json):
            try: os.remove(self.test_json)
            except: pass

    @patch('src.rss_service.feedparser.parse')
    async def test_fetch_feed_success(self, mock_parse):
        """Test successful feed fetching and parsing."""
        url = "http://example.com/rss"
        mock_content = b"<rss>...</rss>"
        mock_feed_data = MagicMock()
        mock_feed_data.entries = [{'title': 'Test Entry'}]
        mock_feed_data.bozo = False
        mock_parse.return_value = mock_feed_data

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = mock_content

        mock_session = MagicMock()
        mock_session.closed = False
        mock_cm = AsyncMock() # Use AsyncMock for the context manager itself!
        mock_cm.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_cm
        
        self.rss_service.session = mock_session

        # Mock run_in_executor to avoid thread switching issues in tests
        loop = asyncio.get_running_loop()
        with patch.object(loop, 'run_in_executor', new=AsyncMock(side_effect=lambda exec, func, *args: func(*args))):
            entries = await self.rss_service.fetch_feed(url)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['title'], 'Test Entry')

    async def test_fetch_feed_http_403(self):
        """Test handling of HTTP 403 Forbidden."""
        url = "http://example.com/rss"

        mock_response = AsyncMock()
        mock_response.status = 403

        mock_session = MagicMock()
        mock_session.closed = False
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_cm
        
        self.rss_service.session = mock_session

        entries = await self.rss_service.fetch_feed(url)
        self.assertEqual(entries, [])

    @patch('src.rss_service.feedparser.parse')
    async def test_fetch_feed_exception_fallback(self, mock_parse):
        """Test fallback when aiohttp fails."""
        url = "http://example.com/rss"
        mock_content = b"<rss>fallback</rss>"
        mock_feed_data = MagicMock()
        mock_feed_data.entries = [{'title': 'Fallback Entry'}]
        mock_feed_data.bozo = False
        mock_parse.return_value = mock_feed_data

        mock_session = MagicMock()
        mock_session.closed = False
        mock_cm = AsyncMock()
        mock_cm.__aenter__.side_effect = aiohttp.ClientError("Net Error")
        mock_session.get.return_value = mock_cm
        
        self.rss_service.session = mock_session

        with patch.object(self.rss_service, '_fetch_feed_blocking', return_value=mock_content) as mock_blocking:
            loop = asyncio.get_running_loop()
            with patch.object(loop, 'run_in_executor', new=AsyncMock(side_effect=lambda exec, func, *args: func(*args))):
                entries = await self.rss_service.fetch_feed(url)
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]['title'], 'Fallback Entry')

if __name__ == '__main__':
    unittest.main()
