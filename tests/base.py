import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TempDataTestCase(unittest.TestCase):
    """Every test runs against a fresh temporary data folder (the real data/ is never touched)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["DID_DATA_DIR"] = self.tmp
        from config import config
        config.ensure_dirs()

    def tearDown(self):
        os.environ.pop("DID_DATA_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)
