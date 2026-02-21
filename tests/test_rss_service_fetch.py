import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rss_service import RSSService

class TestRSSServiceFetch(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_db = 'tests/test_fetch.db'
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.rss_service = RSSService(db_file=self.test_db)

    def tearDown(self):
        if hasattr(self, 'rss_service'):
            # Close connection if it exists
            if self.rss_service.conn:
                self.rss_service.conn.close()

        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                pass

    @patch('src.rss_service.aiohttp.ClientSession')
    @patch('src.rss_service.feedparser.parse')
    async def test_fetch_feed_success(self, mock_parse, mock_session_cls):
        # Setup mocks
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b"feed content"

        # Mock context manager for session.get()
        # session.get() should return a context manager, not a coroutine directly in this usage pattern if we want to mock __aenter__ directly on the return value.
        # However, aiohttp.ClientSession.get IS an async method usually? No, it returns a RequestContextManager.

        mock_session = MagicMock() # Not AsyncMock, because we want control over get return value
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_context_manager.__aexit__.return_value = None

        # Make session.get return the context manager
        mock_session.get.return_value = mock_context_manager

        # mock_session_cls is called to create the session (await self._get_session())
        # In _get_session: self.session = aiohttp.ClientSession()
        # But wait, _get_session is async? No, ClientSession() constructor is synchronous.
        # But _get_session is: async def _get_session(self).
        # Inside it calls self.session = aiohttp.ClientSession().
        # So mock_session_cls() returns mock_session.
        mock_session_cls.return_value = mock_session

        # Mock feedparser result
        mock_feed = MagicMock()
        mock_feed.entries = [{'title': 'Test Entry'}]
        mock_feed.bozo = 0
        mock_parse.return_value = mock_feed

        # Spy on run_in_executor
        loop = asyncio.get_running_loop()

        with patch.object(loop, 'run_in_executor', new=AsyncMock(return_value=mock_feed)) as mock_run_in_executor:
            entries = await self.rss_service.fetch_feed("http://example.com")

            # Verify
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['title'], 'Test Entry')

            # Check if run_in_executor was called correctly
            mock_run_in_executor.assert_called()
            args, _ = mock_run_in_executor.call_args
            self.assertIsNone(args[0])
            self.assertEqual(args[1], mock_parse)
            self.assertEqual(args[2], b"feed content")

    @patch('src.rss_service.aiohttp.ClientSession')
    @patch('src.rss_service.feedparser.parse')
    async def test_fetch_feed_fallback(self, mock_parse, mock_session_cls):
        # Setup mocks to fail aiohttp request
        mock_session = MagicMock()
        # Make session.get return a context manager that raises on __aenter__
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__.side_effect = Exception("Network Error")

        mock_session.get.return_value = mock_context_manager
        mock_session_cls.return_value = mock_session

        # Mock feedparser result for fallback
        mock_feed = MagicMock()
        mock_feed.entries = [{'title': 'Fallback Entry'}]
        mock_feed.bozo = 0
        mock_parse.return_value = mock_feed

        loop = asyncio.get_running_loop()

        with patch.object(loop, 'run_in_executor', new=AsyncMock(return_value=mock_feed)) as mock_run_in_executor:
            entries = await self.rss_service.fetch_feed("http://example.com")

            # Verify
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['title'], 'Fallback Entry')

            # Check if run_in_executor was called with the URL (fallback behavior)
            mock_run_in_executor.assert_called()
            args, _ = mock_run_in_executor.call_args
            self.assertIsNone(args[0])
            self.assertEqual(args[1], mock_parse)
            self.assertEqual(args[2], "http://example.com")

if __name__ == '__main__':
    unittest.main()
