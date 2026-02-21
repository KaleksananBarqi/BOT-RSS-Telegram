import unittest
import ssl
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import src.rss_service to trigger any potential side effects (like the previous monkey-patch)
try:
    from src import rss_service
except ImportError:
    # If src is not a package, try importing directly if path is correct
    import rss_service

class TestSecurity(unittest.TestCase):
    def test_ssl_default_context_is_secure(self):
        """
        Verify that the default SSL context has not been monkey-patched to be unverified.
        """
        if hasattr(ssl, '_create_unverified_context'):
            self.assertNotEqual(
                ssl._create_default_https_context,
                ssl._create_unverified_context,
                "ssl._create_default_https_context should NOT be ssl._create_unverified_context"
            )

    def test_ssl_default_context_settings(self):
        """
        Verify that the default SSL context has secure settings.
        """
        context = ssl.create_default_context()
        self.assertTrue(context.check_hostname, "Default SSL context should check hostname")
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED, "Default SSL context should require certificates")

if __name__ == '__main__':
    unittest.main()
