"""Behaviour of the shared task-state CLI, as an agent or a person uses it."""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "skills" / "task-state" / "scripts" / "state.py"
sys.path.insert(0, str(SCRIPT.parent))
import state  # noqa: E402


class StateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / ".git").mkdir()
        self.old_cwd = os.getcwd()
        os.chdir(self.repo)
        os.environ.pop("ISKANDAR_STATE_DIR", None)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def run_cli(self, *argv, ok=True):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = state.main(list(argv))
        if ok:
            self.assertEqual(code, 0, f"{argv} failed: {err.getvalue()}")
        return code, out.getvalue(), err.getvalue()

    @property
    def tdir(self):
        return self.repo / ".agents" / "state" / "t1"

    def text(self):
        return (self.tdir / "STATE.md").read_text(encoding="utf-8")

    def log_rows(self):
        return state.read_log(self.tdir)

    def open_task(self, tasks=("write the failing test", "fix")):
        self.run_cli("init", "t1", "--title", "Fix cache test", "--goal", "CI stays green with AWAN_CACHE_DIR set")
        self.run_cli("plan", "t1", "--text", "## Proposed Changes\n#### [MODIFY] tests/x.rs")
        self.run_cli("task", "t1", "add", *tasks)

    def to_review(self):
        self.open_task()
        self.run_cli("phase", "t1", "build", "--reason", "plan agreed")
        self.run_cli("task", "t1", "done", "1")
        self.run_cli("task", "t1", "done", "2")
        self.run_cli("phase", "t1", "verify", "--reason", "built")
        self.run_cli("walkthrough", "t1", "--text", "cargo test --test x: 15 passed")
        self.run_cli("phase", "t1", "review", "--reason", "green")


class InitTest(StateTestCase):
    def test_init_writes_state_and_log_in_repo_root(self):
        sub = self.repo / "a" / "b"
        sub.mkdir(parents=True)
        os.chdir(sub)
        self.run_cli("init", "t1", "--title", "T", "--goal", "G")
        self.assertTrue((self.tdir / "STATE.md").exists())
        self.assertEqual(self.log_rows()[0]["decision"], "opened task t1")
        self.assertIn("phase: plan", self.text())
        self.assertIn("```mermaid", self.text())

    def test_init_twice_keeps_the_first(self):
        self.run_cli("init", "t1", "--title", "T", "--goal", "first")
        _, out, _ = self.run_cli("init", "t1", "--title", "T", "--goal", "second")
        self.assertIn("exists", out)
        self.assertIn("first", self.text())
        self.assertEqual(len(self.log_rows()), 1)

    def test_bad_id_is_refused(self):
        code, _, err = self.run_cli("init", "Bad Id", "--title", "T", "--goal", "G", ok=False)
        self.assertEqual(code, 2)
        self.assertIn("bad task id", err)

    def test_env_overrides_location(self):
        other = self.repo / "elsewhere"
        os.environ["ISKANDAR_STATE_DIR"] = str(other)
        try:
            self.run_cli("init", "t1", "--title", "T", "--goal", "G")
        finally:
            os.environ.pop("ISKANDAR_STATE_DIR")
        self.assertTrue((other / "t1" / "STATE.md").exists())


class LifecycleTest(StateTestCase):
    def test_full_lifecycle_reviewed_by_the_other_agent(self):
        self.to_review()
        self.run_cli("phase", "t1", "done", "--reason", "audited", "--by", "antigravity")
        self.assertIn("phase: done", self.text())
        phases = [r["phase"] for r in self.log_rows()]
        self.assertEqual(phases, ["plan", "build", "verify", "review", "done"])
        self.assertEqual(self.run_cli("check", "t1", "--quiet")[0], 0)

    def test_leaving_plan_needs_a_plan_and_tasks(self):
        self.run_cli("init", "t1", "--title", "T", "--goal", "G")
        code, _, err = self.run_cli("phase", "t1", "build", "--reason", "go", ok=False)
        self.assertEqual(code, 2)
        self.assertIn("Plan section", err)
        self.run_cli("plan", "t1", "--text", "do it")
        code, _, err = self.run_cli("phase", "t1", "build", "--reason", "go", ok=False)
        self.assertIn("at least one task", err)

    def test_skipping_a_phase_is_refused(self):
        self.open_task()
        code, _, err = self.run_cli("phase", "t1", "done", "--reason", "yolo", "--by", "human", ok=False)
        self.assertEqual(code, 2)
        self.assertIn("not allowed", err)
        self.assertIn("phase: plan", self.text())

    def test_review_needs_closed_tasks_and_evidence(self):
        self.open_task()
        self.run_cli("phase", "t1", "build", "--reason", "go")
        self.run_cli("phase", "t1", "verify", "--reason", "built")
        code, _, err = self.run_cli("phase", "t1", "review", "--reason", "x", ok=False)
        self.assertIn("open: [1, 2]", err)
        self.run_cli("task", "t1", "done", "1")
        self.run_cli("task", "t1", "skip", "2", "--reason", "covered by task 1")
        code, _, err = self.run_cli("phase", "t1", "review", "--reason", "x", ok=False)
        self.assertIn("Walkthrough", err)

    def test_builder_cannot_close_its_own_work(self):
        self.to_review()
        code, _, err = self.run_cli("phase", "t1", "done", "--reason", "lgtm", "--by", "claude", ok=False)
        self.assertEqual(code, 2)
        self.assertIn("other than the builder (claude)", err)
        self.run_cli("phase", "t1", "done", "--reason", "owner checked", "--by", "human")

    def test_failed_verify_goes_back_to_build(self):
        self.open_task()
        self.run_cli("phase", "t1", "build", "--reason", "go")
        self.run_cli("phase", "t1", "verify", "--reason", "built")
        self.run_cli("phase", "t1", "build", "--reason", "2 tests red", "--evidence", "run 41211952052")
        self.assertEqual(self.log_rows()[-1]["evidence"], "run 41211952052")


class PauseAndHandoffTest(StateTestCase):
    def test_pause_needs_a_next_step_and_resumes_where_it_was(self):
        self.open_task()
        self.run_cli("phase", "t1", "build", "--reason", "go")
        code, _, err = self.run_cli("phase", "t1", "paused", "--reason", "context full", ok=False)
        self.assertIn("handoff note", err)
        self.run_cli("phase", "t1", "paused", "--reason", "context full", "--next", "run cargo test --test x")
        self.assertIn("previous: build", self.text())
        self.assertIn("build --> paused: context full", self.text())
        code, _, err = self.run_cli("phase", "t1", "verify", "--reason", "skip ahead", ok=False)
        self.assertIn("resumes to 'build'", err)
        self.run_cli("phase", "t1", "build", "--reason", "back")
        self.assertNotIn("previous:", self.text())

    def test_handoff_changes_owner_and_records_next_step(self):
        self.open_task()
        self.run_cli("handoff", "t1", "--to", "antigravity", "--for", "build", "--next", "implement task 2",
                     "--files", "core/tests/x.rs", "--questions", "none")
        t = self.text()
        self.assertIn("owner: antigravity", t)
        self.assertIn("Next: implement task 2", t)
        self.assertIn("Key files: core/tests/x.rs", t)
        self.assertEqual(self.log_rows()[-1]["decision"], "handoff claude -> antigravity for build")

    def test_review_handoff_needs_the_review_phase(self):
        # Found in the first Claude run: work done, state still in plan, handed off "for review".
        self.open_task()
        code, _, err = self.run_cli("handoff", "t1", "--to", "antigravity", "--for", "review",
                                    "--next", "review it", ok=False)
        self.assertEqual(code, 2)
        self.assertIn("needs phase review (phase is plan)", err)
        self.assertIn("owner: claude", self.text())
        self.to_review_from_plan()
        self.run_cli("handoff", "t1", "--to", "antigravity", "--for", "review", "--next", "rerun the gate")
        self.assertIn("For: review", self.text())

    def to_review_from_plan(self):
        self.run_cli("phase", "t1", "build", "--reason", "go")
        self.run_cli("task", "t1", "done", "1")
        self.run_cli("task", "t1", "done", "2")
        self.run_cli("phase", "t1", "verify", "--reason", "built")
        self.run_cli("walkthrough", "t1", "--text", "unittest: OK")
        self.run_cli("phase", "t1", "review", "--reason", "green")

    def test_builder_is_whoever_owned_build(self):
        self.open_task()
        self.run_cli("handoff", "t1", "--to", "antigravity", "--for", "build", "--next", "build it")
        self.run_cli("phase", "t1", "build", "--reason", "go")
        self.assertIn("builder: antigravity", self.text())

    def test_resume_logs_a_start_row_naming_other_runs(self):
        self.open_task()
        _, out, _ = self.run_cli("resume", "t1", "--run", "claude-session-2", "--owner", "claude")
        self.assertIn("next task: write the failing test", out)
        last = self.log_rows()[-1]
        self.assertEqual(last["phase"], "start")
        self.assertIn("run claude-session-2", last["evidence"])
        self.assertIn("..", last["why"])
        self.run_cli("resume", "t1", "--run", "claude-session-2")
        self.assertIn("none", self.log_rows()[-1]["why"])


class TasksAndChecksTest(StateTestCase):
    def test_skip_needs_a_reason(self):
        self.open_task()
        code, _, err = self.run_cli("task", "t1", "skip", "1", ok=False)
        self.assertIn("--reason", err)

    def test_hand_edits_survive_and_bad_ones_are_reported(self):
        self.open_task()
        p = self.tdir / "STATE.md"
        t = p.read_text(encoding="utf-8").replace("- [ ] fix", "- [x] fix\n- [-] linux run")
        p.write_text(t.replace("\n", "\r\n"), encoding="utf-8", newline="")
        code, out, _ = self.run_cli("check", "t1", ok=False)
        self.assertEqual(code, 1)
        self.assertIn("task 3 is skipped with no reason", out)
        self.run_cli("task", "t1", "skip", "3", "--reason", "LINUX_CI off")
        self.assertEqual(self.run_cli("check", "t1", "--quiet")[0], 0)
        self.assertIn("- [x] fix", self.text())

    def test_check_catches_a_hand_set_phase_without_evidence(self):
        self.open_task()
        p = self.tdir / "STATE.md"
        p.write_text(p.read_text(encoding="utf-8").replace("phase: plan", "phase: done"), encoding="utf-8")
        code, out, _ = self.run_cli("check", ok=False)
        self.assertIn("done with open tasks", out)
        self.assertIn("Walkthrough: done needs evidence", out)

    def test_check_catches_a_mismatched_id(self):
        self.open_task()
        p = self.tdir / "STATE.md"
        p.write_text(p.read_text(encoding="utf-8").replace("id: t1", "id: t2"), encoding="utf-8")
        _, out, _ = self.run_cli("check", ok=False)
        self.assertIn("does not match folder", out)

    def test_status_lists_open_tasks_by_owner(self):
        self.open_task()
        self.run_cli("init", "t2", "--title", "Other", "--goal", "G", "--owner", "antigravity")
        _, out, _ = self.run_cli("status", "--brief", "--owner", "antigravity")
        self.assertIn("t2", out)
        self.assertNotIn("t1 ", out)

    def test_log_cells_are_sanitised(self):
        self.open_task()
        self.run_cli("log", "t1", "--decision", "=cmd()", "--why", "two\tcells\nand lines", "--result", "ok")
        row = self.log_rows()[-1]
        self.assertEqual(row["decision"], "'=cmd()")
        self.assertEqual(row["why"], "two cells and lines")

    def test_chart_marks_current_and_visited(self):
        self.open_task()
        self.run_cli("phase", "t1", "build", "--reason", "go")
        _, out, _ = self.run_cli("chart", "t1")
        self.assertIn("class build current", out)
        self.assertIn("class plan visited", out)
        self.assertIn("note right of build: owner claude", out)

    def test_agent_briefing(self):
        self.open_task()
        self.run_cli("agent", "t1", "auditor", "--text", "Check the diff against the gate")
        b = (self.tdir / "agents" / "auditor" / "BRIEFING.md").read_text(encoding="utf-8")
        self.assertIn("CI stays green", b)
        self.assertIn("handoff.md", b)
        self.assertTrue((self.tdir / "agents" / "auditor" / "progress.md").exists())


class CliTest(unittest.TestCase):
    def test_runs_as_a_script(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".git").mkdir()
            r = subprocess.run([sys.executable, str(SCRIPT), "status"], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("no open tasks", r.stdout)


if __name__ == "__main__":
    unittest.main()
