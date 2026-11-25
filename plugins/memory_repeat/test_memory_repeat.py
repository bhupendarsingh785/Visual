import unittest
from plugins.memory_repeat.memory_store import MemoryStore

class TestMemoryRepeat(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.store.clear()

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