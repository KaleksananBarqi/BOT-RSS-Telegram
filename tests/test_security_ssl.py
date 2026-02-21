import unittest
import ssl
import sys
from unittest.mock import MagicMock

# Mock missing modules to allow import
mock_modules = ['feedparser', 'aiohttp', 'telegram', 'telegram.request', 'dotenv', 'bs4']
for module in mock_modules:
    sys.modules[module] = MagicMock()

import os
os.environ['BOT_TOKEN'] = 'dummy'
os.environ['GROUP_ID'] = 'dummy'

class TestSecuritySSL(unittest.TestCase):
    def test_ssl_global_verification_enabled(self):
        """Verify that global SSL verification is not disabled."""
        import src.rss_service # Import to trigger any module-level code

        # Check if the global default context is still the original one
        # and hasn't been replaced by an unverified context.

        # In modern Python, ssl._create_default_https_context should be
        # the same as ssl.create_default_context (a function)

        self.assertNotEqual(
            ssl._create_default_https_context,
            getattr(ssl, '_create_unverified_context', None),
            "Global SSL verification is disabled! ssl._create_default_https_context is set to unverified context."
        )

if __name__ == '__main__':
    unittest.main()
