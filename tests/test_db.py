import tempfile
import unittest
from pathlib import Path
from marcus.db import Database

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(str(Path(self.temp.name) / "test.sqlite3"))

    def tearDown(self):
        self.temp.cleanup()

    def test_memories_are_explicit_and_scoped_to_identity(self):
        first = self.db.ensure_identity("telegram", "100", "Alice")
        second = self.db.ensure_identity("telegram", "200", "Bob")
        memory_id = self.db.remember(first, "عاشق ماینکرفتم")
        self.assertEqual(self.db.memories(first)[0], (memory_id, "عاشق ماینکرفتم"))
        self.assertEqual(self.db.memories(second), [])
        self.assertTrue(self.db.forget_memory(first, memory_id))
        self.assertEqual(self.db.memories(first), [])

    def test_link_code_shares_identity_across_platforms(self):
        identity = self.db.ensure_identity("telegram", "100", "Alice")
        self.db.remember(identity, "اسم گربه‌ام پشمالو است")
        code = self.db.create_link_code(identity)
        self.assertTrue(self.db.redeem_link_code("rubika", "r-100", "Alice", code))
        linked = self.db.ensure_identity("rubika", "r-100", "Alice")
        self.assertEqual(linked, identity)
        self.assertEqual(self.db.memories(linked)[0][1], "اسم گربه‌ام پشمالو است")
        self.assertFalse(self.db.redeem_link_code("rubika", "r-200", "Other", code))

    def test_forgetme_removes_linked_identity_data(self):
        identity = self.db.ensure_identity("telegram", "100", "Alice")
        self.db.remember(identity, "یک خاطره")
        code = self.db.create_link_code(identity)
        self.assertTrue(self.db.redeem_link_code("rubika", "r-100", "Alice", code))
        self.db.add_message("telegram", "tg-group", "100", "user", "سلام")
        self.db.add_message("rubika", "rb-group", "r-100", "user", "درود")
        deleted = self.db.forget_user("telegram", "100")
        self.assertEqual(deleted, 2)
        self.assertEqual(self.db.memories(identity), [])
        self.assertEqual(self.db.history("telegram", "tg-group", 10), [])
        self.assertEqual(self.db.history("rubika", "rb-group", 10), [])
        new_identity = self.db.ensure_identity("rubika", "r-100", "Alice")
        self.assertNotEqual(new_identity, identity)

    def test_chat_history_is_separated_by_platform_and_chat(self):
        self.db.add_message("telegram", "group-1", "100", "user", "سلام")
        self.db.add_message("rubika", "group-1", "100", "user", "درود")
        self.assertEqual(self.db.history("telegram", "group-1", 10)[0]["content"], "سلام")
        self.assertEqual(self.db.history("rubika", "group-1", 10)[0]["content"], "درود")

    def test_duplicate_memories_are_not_saved_twice(self):
        identity = self.db.ensure_identity("telegram", "100", "Alice")
        first_id = self.db.remember(identity, "همیشه فارسی و خودمونی جواب بده")
        second_id = self.db.remember(identity, "همیشه فارسی و خودمونی جواب بده")
        self.assertEqual(first_id, second_id)
        self.assertEqual(len(self.db.memories(identity)), 1)

if __name__ == "__main__":
    unittest.main()
