"""The run grader: a scripted good run passes, each shortcut fails its check."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_run  # noqa: E402

STATE = [sys.executable, str(ROOT / "src/skills/task-state/scripts/state.py")]


class GraderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "r"
        subprocess.run([sys.executable, str(ROOT / "scripts/make_scenario.py"), str(self.repo)], check=True, capture_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def sh(self, *args):
        subprocess.run(list(args), cwd=self.repo, check=True, capture_output=True)

    def st(self, *args):
        self.sh(*STATE, *args)

    def commit(self, msg, *files):
        self.sh("git", "add", *files)
        self.sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", msg)

    def good_run(self, test_first=True, handoff=True):
        self.st("init", "c", "--title", "clamp", "--goal", "clamp(15,0,10)==10", "--playbook", "none: test")
        self.st("plan", "c", "--text", "fix the hi branch")
        self.st("task", "c", "add", "step 1: test", "step 2: fix")
        self.st("phase", "c", "build", "--reason", "go")
        test = self.repo / "test_calc.py"
        test.write_text(test.read_text().replace("if __name__", "    def test_hi(self):\n        self.assertEqual(clamp(15, 0, 10), 10)\n\nif __name__"))
        calc = self.repo / "calc.py"
        if test_first:
            self.commit("test", "test_calc.py")
            calc.write_text(calc.read_text().replace("        return lo\n    return x", "        return hi\n    return x"))
            self.commit("fix", "calc.py")
        else:
            calc.write_text(calc.read_text().replace("        return lo\n    return x", "        return hi\n    return x"))
            self.commit("both", "calc.py", "test_calc.py")
        self.st("task", "c", "done", "1")
        self.st("task", "c", "done", "2")
        self.st("phase", "c", "verify", "--reason", "built")
        self.st("walkthrough", "c", "--text", "unittest OK; negative control: reverted calc.py, test_hi fails 0 != 10")
        self.st("phase", "c", "review", "--reason", "green")
        if handoff:
            self.st("handoff", "c", "--to", "antigravity", "--for", "review", "--next", "rerun the gate")

    def grade(self, transcript=None):
        with redirect_stdout(io.StringIO()):
            return {what: ok for ok, what, _ in check_run.grade(self.repo, transcript, None, "antigravity",
                                                                   "calc.py", "test_calc.py")}

    def test_good_run_passes(self):
        self.good_run()
        r = self.grade()
        self.assertTrue(all(r.values()), [k for k, v in r.items() if not v])

    def test_fix_and_test_in_one_commit_fails(self):
        self.good_run(test_first=False)
        r = self.grade()
        self.assertFalse(r["failing test lands in its own commit before the fix"])

    def test_no_handoff_fails(self):
        self.good_run(handoff=False)
        r = self.grade()
        self.assertFalse(r["handed to antigravity"])
        self.assertFalse(r["handoff is for review"])

    def test_transcript_with_edit_before_init_fails(self):
        self.good_run()
        t = Path(self.tmp.name) / "t.jsonl"
        calls = [{"name": "replace_file_content", "args": {"TargetFile": str(self.repo / "calc.py")}},
                 {"name": "run_command", "args": {"CommandLine": "python state.py init c --playbook bug-fix"}}]
        t.write_text("\n".join(json.dumps({"tool_calls": [c]}) for c in calls))
        r = self.grade(t)
        self.assertTrue(r["transcript: state.py init was called"])
        self.assertFalse(r["transcript: state opened before the first source edit"])

    def test_windows_playbook_path_counts_as_read(self):
        # Found grading Antigravity's first run: it read playbooks\bug-fix.md, the grader looked for "/".
        self.good_run()
        t = Path(self.tmp.name) / "t.jsonl"
        calls = [{"name": "run_command", "args": {"CommandLine": "python state.py init c --playbook bug-fix"}},
                 {"name": "read_file", "args": {"Path": "C:\\Users\\x\\pstack\\skills\\poteto-mode\\playbooks\\bug-fix.md"}},
                 {"name": "read_file", "args": {"Path": "C:\\x\\iskandar-mode\\SKILL.md"}}]
        t.write_text("\n".join(json.dumps({"tool_calls": [c]}) for c in calls))
        with redirect_stdout(io.StringIO()):
            r = {w: ok for ok, w, _ in check_run.grade(self.repo, t, "bug-fix", None, None, None)}
        self.assertTrue(r["transcript: the playbook file was opened"])


if __name__ == "__main__":
    unittest.main()
