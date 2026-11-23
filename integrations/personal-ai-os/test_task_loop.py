import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("task_loop", Path(__file__).with_name("task_loop.py"))
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)


class TaskLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.user = Path(self.tmp.name) / "private" / "USER"
        self.user.mkdir(parents=True)
        (self.user / "CONFIG").mkdir()
        self.db = loop.connect(self.user)
        self.addCleanup(self.db.close)

    def test_local_store_is_initialized(self):
        self.assertTrue((self.user / "MEMORY" / "_PERSONAL_AI_OS" / "tasks.sqlite3").is_file())
        self.assertEqual(loop.report(self.db)["event_count"], 0)

    def test_add_tick_once(self):
        task = loop.create_task(self.db, "Read a book", "2026-11-24T09:00:00+08:00")
        self.assertEqual(loop.tick(self.db, "2026-11-24T08:59:00+08:00"), [])
        first = loop.tick(self.db, "2026-11-24T09:00:00+08:00")
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["id"], task["id"])
        self.assertEqual(loop.tick(self.db, "2026-11-24T09:01:00+08:00"), [])
        self.assertEqual(loop.report(self.db)["notification_outbox"], {"queued": 1})

    def test_delivery_acknowledgment_and_completion(self):
        task = loop.create_task(self.db, "Pomodoro", "2026-11-24T10:00:00+08:00")
        loop.tick(self.db, "2026-11-24T10:00:00+08:00")
        with self.assertRaises(ValueError):
            loop.transition(self.db, task["id"], "acknowledged")
        with self.assertRaises(ValueError):
            loop.transition(self.db, task["id"], "delivered")
        loop.transition(self.db, task["id"], "delivered", "provider-123")
        loop.transition(self.db, task["id"], "acknowledged")
        loop.transition(self.db, task["id"], "completed")
        self.assertEqual(loop.report(self.db)["tasks"], {"completed": 1})
        self.assertEqual(loop.report(self.db)["notification_outbox"], {"acknowledged": 1})
        self.assertEqual(loop.report(self.db)["event_count"], 5)

    def test_replay_is_idempotent(self):
        task = loop.create_task(self.db, "Pomodoro", "2026-11-24T10:00:00+08:00")
        loop.tick(self.db, "2026-11-24T10:00:00+08:00")
        loop.transition(self.db, task["id"], "delivered", "provider-123")
        self.assertTrue(loop.transition(self.db, task["id"], "delivered", "provider-123")["already"])
        with self.assertRaises(ValueError):
            loop.transition(self.db, task["id"], "delivered", "different-provider")
        loop.transition(self.db, task["id"], "completed")
        self.assertTrue(loop.transition(self.db, task["id"], "completed")["already"])

    def test_no_naive_time(self):
        with self.assertRaises(ValueError):
            loop.iso_time("2026-11-24T09:00:00")

    def test_reject_public_template(self):
        target = Path(self.tmp.name) / "LifeOS" / "install" / "USER"
        target.mkdir(parents=True)
        (target / "CONFIG").mkdir()
        with self.assertRaises(ValueError):
            loop.connect(target)

    def test_reject_storage_symlink(self):
        # setUp already created a real MEMORY directory via connect;
        # switch only the nested storage folder to a symlink.
        import shutil
        self.db.close()
        storage = self.user / "MEMORY" / "_PERSONAL_AI_OS"
        shutil.rmtree(storage)
        storage.symlink_to(Path(self.tmp.name), target_is_directory=True)
        with self.assertRaises(ValueError):
            loop.connect(self.user)

    def test_complete_before_tick_does_not_queue(self):
        task = loop.create_task(self.db, "Already done", "2026-11-24T09:00:00+08:00")
        loop.transition(self.db, task["id"], "completed")
        self.assertEqual(loop.tick(self.db, "2026-11-24T10:00:00+08:00"), [])

    def test_no_private_task_content_in_report(self):
        loop.create_task(self.db, "confidential test task", "2026-11-24T09:00:00+08:00")
        self.assertNotIn("confidential", str(loop.report(self.db)))


if __name__ == "__main__":
    unittest.main()
