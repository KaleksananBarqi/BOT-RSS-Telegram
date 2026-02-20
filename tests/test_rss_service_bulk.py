import unittest
import os
import sys
from unittest.mock import MagicMock

# Mock missing dependencies
sys.modules['feedparser'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()
sys.modules['bs4'] = MagicMock()

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rss_service import RSSService

class TestRSSServiceBulk(unittest.TestCase):
    def setUp(self):
        self.test_db = 'tests/test_bulk.db'
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.rss_service = RSSService(db_file=self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_filter_new_identifiers(self):
        self.rss_service.mark_as_read("id1")
        self.rss_service.mark_as_read("id2")

        identifiers = ["id1", "id2", "id3", "id4"]
        new_ids = self.rss_service.filter_new_identifiers(identifiers)

        self.assertEqual(new_ids, ["id3", "id4"])

    def test_get_new_entries(self):
        self.rss_service.mark_as_read("id1")

        entries = [
            {'id': 'id1', 'link': 'link1'},
            {'id': 'id2', 'link': 'link2'},
            {'link': 'link3'} # id will be link3
        ]

        new_entries = self.rss_service.get_new_entries(entries)

        self.assertEqual(len(new_entries), 2)
        self.assertEqual(new_entries[0]['id'], 'id2')
        self.assertEqual(new_entries[1].get('id', new_entries[1].get('link')), 'link3')

    def test_filter_new_identifiers_large(self):
        # Test chunking
        num_ids = 2000
        for i in range(500):
            self.rss_service.mark_as_read(f"id_{i}")

        identifiers = [f"id_{i}" for i in range(num_ids)]
        new_ids = self.rss_service.filter_new_identifiers(identifiers)

        self.assertEqual(len(new_ids), 1500)
        self.assertEqual(new_ids[0], "id_500")

if __name__ == '__main__':
    unittest.main()
