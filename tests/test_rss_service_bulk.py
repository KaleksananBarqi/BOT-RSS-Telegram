import unittest
import os
import sys
import asyncio
from unittest.mock import MagicMock

# Mock missing dependencies
sys.modules['feedparser'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()
# sys.modules['bs4'] = MagicMock() # bs4 is used in RSSService, we shouldn't mock it if we can avoid it.
# However, the original test mocked it. But RSSService imports BeautifulSoup from bs4.
# If we mock bs4, RSSService import will get a MagicMock.
# The original test ran fine because RSSService didn't use bs4 in these specific methods?
# Actually filter_new_identifiers and get_new_entries don't use bs4.
# But RSSService import at top level imports bs4. So it must be mocked BEFORE import.
# The original file has imports AFTER mock.

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rss_service import RSSService

class TestRSSServiceBulk(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_db = 'tests/test_bulk.db'
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.rss_service = RSSService(db_file=self.test_db)
        await self.rss_service.init()

    async def asyncTearDown(self):
        await self.rss_service.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists(self.test_db + "-wal"):
            os.remove(self.test_db + "-wal")
        if os.path.exists(self.test_db + "-shm"):
            os.remove(self.test_db + "-shm")

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
        # In the original test: self.assertEqual(new_entries[1].get('id', new_entries[1].get('link')), 'link3')
        self.assertEqual(new_entries[1].get('id', new_entries[1].get('link')), 'link3')

    async def test_filter_new_identifiers_large(self):
        # Test chunking
        num_ids = 2000
        # Insert 500
        for i in range(500):
            await self.rss_service.mark_as_read(f"id_{i}")

        identifiers = [f"id_{i}" for i in range(num_ids)]
        new_ids = await self.rss_service.filter_new_identifiers(identifiers)

        self.assertEqual(len(new_ids), 1500)
        self.assertEqual(new_ids[0], "id_500")

if __name__ == '__main__':
    unittest.main()
