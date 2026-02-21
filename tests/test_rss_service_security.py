import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from src.rss_service import RSSService
import urllib.request

class FailingContextManager:
    async def __aenter__(self):
        raise Exception("Aiohttp failed")
    async def __aexit__(self, exc_type, exc, tb):
        pass

class TestRSSServiceSecurity(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = RSSService()

    async def asyncTearDown(self):
        # close() awaits session.close(). Check if it's a mock and handle appropriately.
        if isinstance(self.service.session, MagicMock):
             self.service.session.close = AsyncMock()
        await self.service.close()

    @patch('src.rss_service.feedparser.parse')
    @patch('urllib.request.urlopen')
    async def test_fallback_timeout(self, mock_urlopen, mock_feedparser):
        # Setup mocks
        url = "http://example.com/feed"

        # Mock aiohttp failure using a custom context manager that raises
        mock_session = MagicMock()
        mock_session.closed = False  # Important! Otherwise _get_session recreates session
        mock_session.get.return_value = FailingContextManager()
        mock_session.close = AsyncMock() # Make close awaitable

        self.service.session = mock_session

        # Mock urlopen context manager
        mock_urlopen_ctx = MagicMock()
        mock_urlopen.return_value = mock_urlopen_ctx
        mock_urlopen_ctx.__enter__.return_value.read.return_value = b"mock content"
        mock_urlopen_ctx.__exit__.return_value = None

        # Mock feedparser
        mock_feedparser.return_value.entries = []
        mock_feedparser.return_value.bozo = 0

        # Execute
        await self.service.fetch_feed(url)

        # Verify fallback was used
        # We expect urlopen to be called with timeout=30
        if mock_urlopen.call_count == 0:
             self.fail("urllib.request.urlopen was not called. Feedparser fallback might not have triggered or used urllib.")

        # Check arguments
        args, kwargs = mock_urlopen.call_args

        # Verify timeout
        self.assertEqual(kwargs.get('timeout'), 30, "Timeout should be set to 30 seconds")

        # Verify User-Agent
        if args and isinstance(args[0], urllib.request.Request):
            req = args[0]
            self.assertIn('User-agent', req.headers)

        # Verify feedparser was called with the content bytes
        mock_feedparser.assert_called_with(b"mock content")

if __name__ == '__main__':
    unittest.main()
