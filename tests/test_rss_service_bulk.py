import unittest
import os
import sys
import asyncio
from unittest.mock import MagicMock

# Set dummy environment variables to bypass config check
os.environ['BOT_TOKEN'] = 'dummy_token'
os.environ['GROUP_ID'] = 'dummy_group_id'

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock environment variables for config
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['GROUP_ID'] = 'test_group'

from src.rss_service import RSSService

class TestRSSServiceBulk(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_db = 'tests/test_bulk.db'
        # Clean up any existing DB files
        for ext in ['', '-wal', '-shm']:
            f = self.test_db + ext
            if os.path.exists(f):
                try:
                    os.remove(f)
                except PermissionError:
                    pass
        self.rss_service = RSSService(db_file=self.test_db)
        await self.rss_service.initialize()

    async def asyncTearDown(self):
        if hasattr(self, 'rss_service') and self.rss_service.conn:
            await self.rss_service.close()

        for ext in ['', '-wal', '-shm']:
            f = self.test_db + ext
            if os.path.exists(f):
                try:
                    os.remove(f)
                except PermissionError:
                    pass

    async def test_filter_new_identifiers(self):
        await self.rss_service.mark_as_read("id1")
        await self.rss_service.mark_as_read("id2")

        identifiers = ["id1", "id2", "id3", "id4"]
        new_ids = await self.rss_service.filter_new_identifiers(identifiers)

        self.assertEqual(new_ids, ["id3", "id4"])

    async def test_get_new_entries(self):
        await self.rss_service.mark_as_read("id1")

        entries = [
            {'id': 'id1', 'link': 'link1'},
            {'id': 'id2', 'link': 'link2'},
            {'link': 'link3'} # id will be link3
        ]

        new_entries = await self.rss_service.get_new_entries(entries)

        self.assertEqual(len(new_entries), 2)
        self.assertEqual(new_entries[0]['id'], 'id2')
        self.assertEqual(new_entries[1].get('id', new_entries[1].get('link')), 'link3')

    async def test_filter_new_identifiers_large(self):
        # Test chunking
        num_ids = 2000
        for i in range(500):
            await self.rss_service.mark_as_read(f"id_{i}")

        identifiers = [f"id_{i}" for i in range(num_ids)]
        new_ids = await self.rss_service.filter_new_identifiers(identifiers)

        self.assertEqual(len(new_ids), 1500)
        self.assertEqual(new_ids[0], "id_500")

if __name__ == '__main__':
    unittest.main()
