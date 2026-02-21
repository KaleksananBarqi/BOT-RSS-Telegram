import unittest
import os
import shutil
import sqlite3
import sys
import json
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rss_service import RSSService

class TestRSSService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use a temporary DB file for testing
        self.test_db = 'tests/test_bot.db'
        self.test_json = 'tests/test_history.json'

        # Ensure clean state
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists(self.test_json):
            os.remove(self.test_json)

        self.rss_service = RSSService(db_file=self.test_db, json_history_file=self.test_json)
        await self.rss_service.init()

    async def asyncTearDown(self):
        # Cleanup
        if hasattr(self, 'rss_service'):
            # Close connection if it exists
            await self.rss_service.close()
        
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                pass # Silently fail if still locked
        if os.path.exists(self.test_json):
            try:
                os.remove(self.test_json)
            except PermissionError:
                pass
        # Cleanup WAL/SHM files if any
        if os.path.exists(self.test_db + "-wal"):
            os.remove(self.test_db + "-wal")
        if os.path.exists(self.test_db + "-shm"):
            os.remove(self.test_db + "-shm")

    async def test_init_db(self):
        """Test if DB is created."""
        self.assertTrue(os.path.exists(self.test_db))
        # Verify using standard sqlite3 to ensure file integrity
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

        e7 = Entry({
            'media_thumbnail': [{'url': 'http://example.com/thumb.jpg'}],
            'enclosures': [{'url': 'http://example.com/enc.jpg', 'type': 'image/jpeg'}]
        })
        self.assertEqual(self.rss_service.extract_image(e7), 'http://example.com/thumb.jpg')

    def test_filter_entries_by_age(self):
        now = datetime.now(timezone.utc)

        # Helper class
        class Entry:
            def __init__(self, time_tuple):
                self.published_parsed = time_tuple

        # Entry 1: New (1 hour ago)
        e1_time = now - timedelta(hours=1)
        e1 = Entry(e1_time.timetuple())

        # Entry 2: Old (25 hours ago)
        e2_time = now - timedelta(hours=25)
        e2 = Entry(e2_time.timetuple())

        entries = [e1, e2]
        filtered = self.rss_service.filter_entries_by_age(entries, max_hours=24)

        self.assertIn(e1, filtered)
        self.assertNotIn(e2, filtered)

    async def test_migration(self):
        # Create a dummy json file
        data = ["old_id_1", "old_id_2"]
        with open(self.test_json, 'w') as f:
            json.dump(data, f)

        # Re-init service to trigger migration
        # We need to make sure DB is empty/deleted first
        await self.rss_service.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        service = RSSService(db_file=self.test_db, json_history_file=self.test_json)
        await service.init()

        self.assertFalse(await service.is_new("old_id_1"))
        self.assertFalse(await service.is_new("old_id_2"))
        self.assertTrue(await service.is_new("new_id"))
        
        await service.close()

if __name__ == '__main__':
    unittest.main()
