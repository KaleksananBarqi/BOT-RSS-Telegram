import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Set dummy environment variables to bypass config check
os.environ['BOT_TOKEN'] = 'dummy_token'
os.environ['GROUP_ID'] = 'dummy_group_id'

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rss_service import RSSService

class MockEntry(dict):
    """Helper class to simulate feedparser entry (dict + attribute access)."""
    def __getattr__(self, name):
        if name in self:
            return self[name]
        return None

class TestRSSParseEntry(unittest.TestCase):
    def setUp(self):
        # Use a temporary DB file path to avoid os.makedirs error
        self.test_db = 'tests/temp_parse_test.db'
        self.rss_service = RSSService(db_file=self.test_db, json_history_file=':memory:')

    def tearDown(self):
        # Clean up the temporary DB file
        if hasattr(self, 'rss_service') and self.rss_service.conn:
             self.rss_service.conn.close()

        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass

        # Cleanup WAL files
        if os.path.exists(f"{self.test_db}-shm"):
            try:
                os.remove(f"{self.test_db}-shm")
            except OSError:
                pass
        if os.path.exists(f"{self.test_db}-wal"):
            try:
                os.remove(f"{self.test_db}-wal")
            except OSError:
                pass

    def test_parse_entry_basic(self):
        """Test basic parsing of a standard entry."""
        entry = MockEntry({
            'id': 'unique_id_123',
            'title': 'Test Title',
            'link': 'http://example.com/article',
            'published': 'Mon, 01 Jan 2024 12:00:00 GMT',
            'summary': 'This is a summary.',
            'media_content': [] # Mock extract_image call later
        })

        # Mock extract_image to return a known value
        self.rss_service.extract_image = MagicMock(return_value='http://example.com/image.jpg')

        result = self.rss_service.parse_entry(entry)

        self.assertEqual(result['id'], 'unique_id_123')
        self.assertEqual(result['title'], 'Test Title')
        self.assertEqual(result['link'], 'http://example.com/article')
        self.assertEqual(result['published'], 'Mon, 01 Jan 2024 12:00:00 GMT')
        self.assertEqual(result['summary'], 'This is a summary.')
        self.assertEqual(result['image_url'], 'http://example.com/image.jpg')

        # Check that extract_image was called with the entry and some soup object
        self.rss_service.extract_image.assert_called_once()
        args, kwargs = self.rss_service.extract_image.call_args
        self.assertEqual(args[0], entry)
        self.assertIn('soup', kwargs)

    def test_parse_entry_html_cleaning(self):
        """Test that HTML tags are removed from summary."""
        entry = MockEntry({
            'summary': '<p>This is <b>bold</b> and <a href="#">link</a>.</p>'
        })
        self.rss_service.extract_image = MagicMock(return_value=None)

        result = self.rss_service.parse_entry(entry)

        self.assertEqual(result['summary'], 'This is bold and link.')

    def test_parse_entry_truncation(self):
        """Test that summary is truncated to 300 chars."""
        long_summary = "A" * 301
        entry = MockEntry({'summary': long_summary})
        self.rss_service.extract_image = MagicMock(return_value=None)

        result = self.rss_service.parse_entry(entry)

        self.assertEqual(len(result['summary']), 303) # 300 chars + "..."
        self.assertTrue(result['summary'].endswith('...'))
        self.assertEqual(result['summary'][:300], "A" * 300)

    def test_parse_entry_fallback_description(self):
        """Test that description is used if summary is missing/empty."""
        entry = MockEntry({
            'summary': '',
            'description': 'Description fallback.'
        })
        self.rss_service.extract_image = MagicMock(return_value=None)

        result = self.rss_service.parse_entry(entry)

        self.assertEqual(result['summary'], 'Description fallback.')

    def test_parse_entry_missing_fields(self):
        """Test behavior when optional fields are missing."""
        entry = MockEntry({}) # Empty entry
        self.rss_service.extract_image = MagicMock(return_value=None)

        result = self.rss_service.parse_entry(entry)

        self.assertIsNone(result['id']) # entry.get('id', entry.get('link')) -> None if both missing
        self.assertEqual(result['title'], 'No Title')
        self.assertEqual(result['link'], '')
        self.assertEqual(result['published'], '')
        self.assertEqual(result['summary'], '')
        self.assertIsNone(result['image_url'])

    def test_parse_entry_id_fallback_link(self):
        """Test that link is used as ID if ID is missing."""
        entry = MockEntry({
            'link': 'http://example.com/unique',
            'title': 'Test'
        })
        self.rss_service.extract_image = MagicMock(return_value=None)

        result = self.rss_service.parse_entry(entry)

        self.assertEqual(result['id'], 'http://example.com/unique')

if __name__ == '__main__':
    unittest.main()
