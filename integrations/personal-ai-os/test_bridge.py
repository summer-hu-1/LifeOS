import tempfile
from pathlib import Path
import importlib.util
import unittest

SPEC = importlib.util.spec_from_file_location("bridge", Path(__file__).with_name("bridge.py"))
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / "export"
        self.source.mkdir()
        self.target = root / "lifeos" / "USER"
        self.target.mkdir(parents=True)
        (self.target / "CONFIG").mkdir()
        (self.source / "GOALS.md").write_text("# private test goal", encoding="utf-8")

    def test_default_dry_run_does_not_write(self):
        report = bridge.stage(self.source, self.target)
        self.assertTrue(report["ok"])
        self.assertTrue(report["dry_run"])
        self.assertFalse((self.target / "IMPORTS").exists())

    def test_explicit_apply_stages_file(self):
        report = bridge.stage(self.source, self.target, apply=True)
        self.assertTrue(report["ok"])
        self.assertEqual((self.target / "IMPORTS" / "PERSONAL_AI_OS" / "GOALS.md").read_text(), "# private test goal")
        self.assertEqual(next(x for x in report["files"] if x["file"] == "GOALS.md")["status"], "staged")

    def test_reimport_does_not_replace(self):
        bridge.stage(self.source, self.target, apply=True)
        report = bridge.stage(self.source, self.target, apply=True)
        self.assertTrue(report["ok"])
        self.assertEqual(next(x for x in report["files"] if x["file"] == "GOALS.md")["status"], "identical")

    def test_conflict_rejects_apply(self):
        bridge.stage(self.source, self.target, apply=True)
        path = self.target / "IMPORTS" / "PERSONAL_AI_OS" / "GOALS.md"
        path.write_text("newer notes")
        report = bridge.stage(self.source, self.target, apply=True)
        self.assertFalse(report["ok"])
        self.assertEqual(path.read_text(), "newer notes")

    def test_reject_symlink_input(self):
        (self.source / "GOALS.md").unlink()
        (self.source / "GOALS.md").symlink_to(self.target / "CONFIG")
        with self.assertRaises(ValueError):
            bridge.stage(self.source, self.target, apply=True)

    def test_reject_symlink_target(self):
        (self.target / "IMPORTS").symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            bridge.stage(self.source, self.target, apply=True)

    def test_reject_missing_notes(self):
        (self.source / "GOALS.md").unlink()
        with self.assertRaises(ValueError):
            bridge.stage(self.source, self.target)

    def test_reject_template_destination(self):
        template = Path(self.tmp.name) / "LifeOS" / "install" / "USER"
        template.mkdir(parents=True)
        (template / "CONFIG").mkdir()
        with self.assertRaises(ValueError):
            bridge.stage(self.source, template, apply=True)


if __name__ == "__main__":
    unittest.main()
