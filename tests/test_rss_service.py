import unittest
import os
import shutil
import sqlite3
import sys
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock

# Set dummy environment variables to bypass config check
os.environ['BOT_TOKEN'] = 'dummy_token'
os.environ['GROUP_ID'] = 'dummy_group_id'

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock environment variables for config
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['GROUP_ID'] = 'test_group'

from src.rss_service import RSSService

class TestRSSService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use a temporary DB file for testing
        self.test_db = 'tests/test_bot.db'
        self.test_json = 'tests/test_history.json'

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
        # We need to initialize for DB tests
        await self.rss_service.initialize()

    async def asyncTearDown(self):
        # Cleanup
        if hasattr(self, 'rss_service'):
            await self.rss_service.close()
        
        for ext in ['', '-shm', '-wal']:
            path = self.test_db + ext
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        if os.path.exists(self.test_json):
            try:
                os.remove(self.test_json)
            except OSError:
                pass

    def test_init_db(self):
        """Test if DB is created."""
        self.assertTrue(os.path.exists(self.test_db))
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
        self.assertIsNotNone(c.fetchone())
        conn.close()

    async def test_is_new_and_mark_as_read(self):
        entry_id = "test_entry_1"

        # Should be new initially
        self.assertTrue(await self.rss_service.is_new(entry_id))

        # Mark as read
        await self.rss_service.mark_as_read(entry_id)

        # Should not be new anymore
        self.assertFalse(await self.rss_service.is_new(entry_id))

    def test_extract_image(self):
        # Helper class to simulate feedparser entry
        class Entry(dict):
            def __getattr__(self, name):
                if name in self: return self[name]
                return None

        # Case 1: Media Content
        e1 = Entry({
            'media_content': [{'url': 'http://example.com/img.jpg', 'type': 'image/jpeg'}]
        })
        self.assertEqual(self.rss_service.extract_image(e1), 'http://example.com/img.jpg')

        # Case 2: Summary Image
        e2 = Entry({'summary': '<p>Text <img src="http://example.com/summary.jpg"> end</p>'})
        self.assertEqual(self.rss_service.extract_image(e2), 'http://example.com/summary.jpg')

        # Case 3: No image
        e3 = Entry({'summary': 'No image here'})
        self.assertIsNone(self.rss_service.extract_image(e3))

        # Case 4: Media Thumbnail
        e4 = Entry({
            'media_thumbnail': [{'url': 'http://example.com/thumb.jpg'}]
        })
        self.assertEqual(self.rss_service.extract_image(e4), 'http://example.com/thumb.jpg')

        # Case 5: Enclosures
        e5 = Entry({
            'enclosures': [{'url': 'http://example.com/enc.jpg', 'type': 'image/jpeg'}]
        })
        self.assertEqual(self.rss_service.extract_image(e5), 'http://example.com/enc.jpg')

        # Case 6: Priority (Media Content > Media Thumbnail > Enclosures)
        e6 = Entry({
            'media_content': [{'url': 'http://example.com/content.jpg', 'type': 'image/jpeg'}],
            'media_thumbnail': [{'url': 'http://example.com/thumb.jpg'}],
            'enclosures': [{'url': 'http://example.com/enc.jpg', 'type': 'image/jpeg'}]
        })
        self.assertEqual(self.rss_service.extract_image(e6), 'http://example.com/content.jpg')

        # Case 7: Enclosure priority
        e7 = Entry({
            'media_thumbnail': [{'url': 'http://example.com/thumb.jpg'}],
            'enclosures': [{'url': 'http://example.com/enc.jpg', 'type': 'image/jpeg'}]
        })
        self.assertEqual(self.rss_service.extract_image(e7), 'http://example.com/thumb.jpg')

        # Case 8: Empty Media Thumbnail
        e8 = Entry({
            'media_thumbnail': []
        })
        self.assertIsNone(self.rss_service.extract_image(e8))

    def test_filter_entries_by_age(self):
        now = datetime.now(timezone.utc)

        class MockEntry(dict):
            def __getattr__(self, name):
                if name in self: return self[name]
                return None

        # Entry 1: New (1 hour ago)
        e1_time = now - timedelta(hours=1)
        e1 = MockEntry({'published_parsed': e1_time.timetuple()})

        # Entry 2: Old (25 hours ago)
        e2_time = now - timedelta(hours=25)
        e2 = MockEntry({'published_parsed': e2_time.timetuple()})

        entries = [e1, e2]
        filtered = self.rss_service.filter_entries_by_age(entries, max_hours=24)

        self.assertIn(e1, filtered)
        self.assertNotIn(e2, filtered)

    def test_filter_entries_by_age_malformed_date(self):
        """Test handling of malformed dates in filter_entries_by_age."""
        class MockEntry(dict):
            def __getattr__(self, name):
                if name in self: return self[name]
                return None

        # Entry with invalid month (13)
        e_malformed = MockEntry({'published_parsed': (2024, 13, 1, 12, 0, 0, 0, 0, 0)})
        
        entries = [e_malformed]
        filtered = self.rss_service.filter_entries_by_age(entries, max_hours=24)
        
        # Should be kept (considered valid fallback)
        self.assertIn(e_malformed, filtered)

    async def test_migration(self):
        # Create a dummy json file
        migration_json = 'tests/test_migration.json'
        migration_db = 'tests/test_migration.db'
        
        data = ["old_id_1", "old_id_2"]
        with open(migration_json, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        # Re-init service with different files to trigger migration
        service = RSSService(db_file=migration_db, json_history_file=migration_json)
        await service.initialize()

        self.assertFalse(await service.is_new("old_id_1"))
        self.assertFalse(await service.is_new("old_id_2"))
        self.assertTrue(await service.is_new("new_id"))
        
        await service.close()
        
        # Cleanup migration specific files
        for ext in ['', '-shm', '-wal']:
            if os.path.exists(migration_db + ext):
                try: os.remove(migration_db + ext)
                except: pass
        if os.path.exists(migration_json):
            os.remove(migration_json)

    async def test_is_new_database_error(self):
        """Test that is_new returns False when a database error occurs."""
        with patch.object(self.rss_service, 'conn', new_callable=AsyncMock) as mock_conn:
            mock_cursor = AsyncMock()
            mock_conn.cursor.return_value = mock_cursor
            # aiosqlite execute is async
            mock_cursor.execute.side_effect = sqlite3.Error("Simulated database error")

            result = await self.rss_service.is_new("some_entry_id")

            self.assertFalse(result)
            mock_conn.cursor.assert_called_once()

    def test_extract_image_edge_cases(self):
        """Test edge cases for extract_image including malformed feeds."""
        class Entry(dict):
            def __getattr__(self, name):
                if name in self:
                    return self[name]
                return None

        # Malformed HTML in summary - should not crash
        e1 = Entry({'summary': '<p>Unclosed <img src="http://example.com/test.jpg"></p>'})
        result = self.rss_service.extract_image(e1)
        self.assertEqual(result, 'http://example.com/test.jpg')

        # Malformed HTML with broken tags
        e2 = Entry({'summary': '<p><<img src="http://example.com/broken.jpg"</p>'})
        result = self.rss_service.extract_image(e2)
        self.assertEqual(result, 'http://example.com/broken.jpg')

        # Media content missing 'url' key - should not crash, should skip
        e3 = Entry({
            'media_content': [{'type': 'image/jpeg'}]
        })
        result = self.rss_service.extract_image(e3)
        self.assertIsNone(result)

        # Media thumbnail missing 'url' key - should not crash
        e4 = Entry({
            'media_thumbnail': [{'width': '100'}]
        })
        result = self.rss_service.extract_image(e4)
        self.assertIsNone(result)

        # Enclosure missing 'url' key - should not crash
        e5 = Entry({
            'enclosures': [{'type': 'image/jpeg'}]
        })
        result = self.rss_service.extract_image(e5)
        self.assertIsNone(result)

        # img tag without src attribute
        e6 = Entry({'summary': '<p><img alt="no source"></p>'})
        result = self.rss_service.extract_image(e6)
        self.assertIsNone(result)

        # media_content with medium='image' but no type
        e7 = Entry({
            'media_content': [{'url': 'http://example.com/medium.jpg', 'medium': 'image'}]
        })
        result = self.rss_service.extract_image(e7)
        self.assertEqual(result, 'http://example.com/medium.jpg')

        # Multiple img tags - should return first one
        e8 = Entry({
            'summary': '<img src="http://example.com/first.jpg"><img src="http://example.com/second.jpg">'
        })
        result = self.rss_service.extract_image(e8)
        self.assertEqual(result, 'http://example.com/first.jpg')

        # Empty summary and description
        e9 = Entry({'summary': '', 'description': ''})
        result = self.rss_service.extract_image(e9)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
