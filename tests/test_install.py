"""Installing into a fresh home and a fresh repo, twice (idempotent)."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install  # noqa: E402

HAVE_PSTACK = (ROOT / ".cache/cursor-plugins/harness/pstack/claude-code/skills/poteto-mode/SKILL.md").exists()


def quiet(fn, *a):
    with redirect_stdout(io.StringIO()):
        return fn(*a)


@unittest.skipUnless(HAVE_PSTACK, "pstack not fetched: python3 scripts/fetch_pstack.py")
class AntigravityInstallTest(unittest.TestCase):
    def test_copy_install_into_a_home_keeps_other_settings(self):
        with tempfile.TemporaryDirectory() as home:
            cfg = Path(home) / ".gemini/config/config.json"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(json.dumps({"plugins": {"gdocs": {"installedFrom": {"id": "x"}}}, "userSettings": {"a": 1}}))
            for _ in range(2):
                self.assertEqual(quiet(install.install_antigravity, Path(home), True), 0)
            plugins = Path(home) / ".gemini/config/plugins"
            self.assertTrue((plugins / "pstack/skills/poteto-mode/SKILL.md").exists())
            self.assertTrue((plugins / "iskandar-stack/skills/iskandar-mode/SKILL.md").exists())
            self.assertTrue((plugins / "iskandar-stack/plugin.json").exists())
            self.assertTrue((plugins / "iskandar-stack/docs/harness/antigravity.md").exists())
            data = json.loads(cfg.read_text())
            self.assertEqual(data["userSettings"], {"a": 1})
            self.assertIn("installedFrom", data["plugins"]["gdocs"])
            self.assertTrue(data["plugins"]["pstack"]["enabled"])
            self.assertTrue(data["plugins"]["iskandar-stack"]["enabled"])
            self.assertTrue(cfg.with_suffix(".json.bak-iskandar-stack").exists())


class ClaudeProjectInstallTest(unittest.TestCase):
    def test_merges_into_existing_settings(self):
        with tempfile.TemporaryDirectory() as repo:
            p = Path(repo) / ".claude/settings.json"
            p.parent.mkdir()
            p.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}, "enabledPlugins": {"other@x": True}}))
            for _ in range(2):
                quiet(install.install_claude_project, Path(repo))
            data = json.loads(p.read_text())
            self.assertEqual(data["permissions"], {"allow": ["Bash(ls)"]})
            self.assertEqual(data["enabledPlugins"],
                             {"other@x": True, "pstack@cursor-plugins": True, "iskandar-stack@iskandar-stack": True})
            self.assertEqual(data["extraKnownMarketplaces"]["cursor-plugins"]["source"]["repo"], "cursor/plugins")


if __name__ == "__main__":
    unittest.main()
