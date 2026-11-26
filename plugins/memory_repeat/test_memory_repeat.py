import os
import tempfile
import unittest

from plugins.memory_repeat import memory_store


class TestMemoryRepeat(unittest.TestCase):
    def setUp(self):
        self._original_path = memory_store.MEMORY_FILE
        self._temp_dir = tempfile.TemporaryDirectory()
        memory_store.MEMORY_FILE = os.path.join(self._temp_dir.name, "last_statement.json")
        self.store = memory_store.MemoryStore()

    def tearDown(self):
        memory_store.MEMORY_FILE = self._original_path
        self._temp_dir.cleanup()

    def test_store_and_recall(self):
        self.store.store_last("namaste boss")
        self.assertEqual(self.store.recall_last(), "namaste boss")

    def test_clear(self):
        self.store.store_last("hello")
        self.store.clear()
        self.assertIsNone(self.store.recall_last())

    def test_empty_state(self):
        self.assertIsNone(self.store.recall_last())


if __name__ == "__main__":
    unittest.main()
