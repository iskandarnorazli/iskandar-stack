#!/usr/bin/env python3
"""Grade one agent run of the iskandar-mode workflow from what it left behind.

  check_run.py <repo> [--transcript FILE] [--playbook bug-fix] [--reviewer antigravity]
               [--source calc.py] [--tests test_calc.py]

Reads the repo's .agents/state/, its git history, and optionally the agent's
transcript (Claude Code stream-json, or Antigravity's transcript_full.jsonl).
Prints one line per check and exits 1 if any fails. The same checks apply to
Claude and Antigravity, so their runs compare directly.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src" / "skills" / "task-state" / "scripts"))
import state  # noqa: E402

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "replace_file_content", "write_to_file", "edit_file", "write_file"}
SHELL_TOOLS = {"Bash", "run_command"}


def tool_calls(path: Path):
    """(name, input) in order, from either harness's transcript."""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "assistant":  # Claude Code stream-json
            for c in d.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    yield c["name"], c.get("input", {})
        for tc in d.get("tool_calls") or []:  # Antigravity transcript
            a = tc.get("args") or tc.get("arguments") or {}
            if isinstance(a, str):
                try:
                    a = json.loads(a)
                except ValueError:
                    a = {}
            yield tc.get("name", ""), a


def edited_path(name: str, inp: dict) -> str:
    return str(inp.get("file_path") or inp.get("TargetFile") or inp.get("Path") or "")


def shell_text(inp: dict) -> str:
    return str(inp.get("command") or inp.get("CommandLine") or "")


def git(repo: Path, *args) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True).stdout


def grade(repo: Path, transcript, playbook, reviewer, source, tests) -> list:
    results = []

    def check(ok: bool, what: str, detail: str = ""):
        results.append((bool(ok), what, detail))

    root = repo / ".agents" / "state"
    tasks = sorted(p for p in root.iterdir() if (p / "STATE.md").exists()) if root.exists() else []
    check(len(tasks) == 1, "one task state folder", f"found {len(tasks)}")
    if not tasks:
        return results
    d = tasks[0]
    st = state.load(d)
    rows = state.read_log(d)
    probs = state.problems(st, d)
    check(not probs, "state.py check is clean", "; ".join(probs))
    if playbook:
        check(st.meta.get("playbook") == playbook, f"playbook is {playbook}", f"got {st.meta.get('playbook')!r}")
        check(any(t.text.startswith("step 1:") for t in st.tasks), "the playbook's steps are the tasks")
    phases = [r["phase"] for r in rows if r["phase"] in state.PHASES]
    order = [p for p in ("plan", "build", "verify", "review") if p in phases]
    check(order == ["plan", "build", "verify", "review"], "phases went plan, build, verify, review", " -> ".join(phases))
    check(st.phase == "review", "task ends in review, not closed by its builder", f"phase {st.phase}")
    check(all(t.status != "open" for t in st.tasks), "every task done or skipped with a reason")
    skips = [t for t in st.tasks if t.status == "skip"]
    check(all(t.reason for t in skips), "each skip has a reason")
    check(bool(st.sections.get("Walkthrough", "").strip()), "walkthrough holds evidence")
    if reviewer:
        check(st.meta.get("owner") == reviewer, f"handed to {reviewer}", f"owner {st.meta.get('owner')}")
        check("For: review" in st.sections.get("Handoff", ""), "handoff is for review")
        check(st.meta.get("builder") not in ("", reviewer), "builder is not the reviewer", f"builder {st.meta.get('builder')}")
    check(any("negative" in (r["decision"] + r["why"] + r["evidence"] + r["result"]).lower() for r in rows)
          or "negative" in st.sections.get("Walkthrough", "").lower()
          or "revert" in st.sections.get("Walkthrough", "").lower(),
          "negative control recorded")

    if source and tests:
        log = git(repo, "log", "--reverse", "--format=%H", "--", source, tests).split()[1:]
        def touched(c):  # whole paths: "calc.py" must not match "test_calc.py"
            return set(git(repo, "show", "--name-only", "--format=", c).split())
        first_test = next((c for c in log if tests in touched(c)), None)
        first_fix = next((c for c in log if source in touched(c)), None)
        ok = first_test is not None and first_fix is not None and log.index(first_test) <= log.index(first_fix)
        detail = "same commit" if first_test == first_fix else ""
        check(ok, "failing test committed no later than the fix", detail)
        check(first_test != first_fix, "failing test lands in its own commit before the fix", detail)

    if transcript:
        calls = list(tool_calls(transcript))
        init_at = next((i for i, (n, a) in enumerate(calls) if n in SHELL_TOOLS and "state.py" in shell_text(a)
                        and " init " in f" {shell_text(a)} "), None)
        edit_at = next((i for i, (n, a) in enumerate(calls) if n in EDIT_TOOLS and source and edited_path(n, a).endswith(source)),
                       None)
        sed_at = next((i for i, (n, a) in enumerate(calls) if n in SHELL_TOOLS and source and source in shell_text(a)
                       and any(k in shell_text(a) for k in ("open(", "sed -i", "> " + source, ".write("))), None)
        first_edit = min(x for x in (edit_at, sed_at, 10**9) if x is not None)
        check(init_at is not None, "transcript: state.py init was called")
        check(init_at is not None and init_at < first_edit, "transcript: state opened before the first source edit",
              f"init at call {init_at}, first edit at {first_edit if first_edit < 10**9 else 'none'}")
        read_mode = any("iskandar-mode" in json.dumps(a) for _, a in calls)
        check(read_mode, "transcript: the iskandar-mode skill was read")
        # Windows paths arrive with backslashes (JSON-escaped); compare with / only.
        read_playbook = any(f"playbooks/{playbook}.md" in json.dumps(a).replace("\\\\", "/").replace("\\", "/")
                            for _, a in calls) if playbook else True
        check(read_playbook, "transcript: the playbook file was opened")
    return results


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("repo", type=Path)
    p.add_argument("--transcript", type=Path)
    p.add_argument("--playbook")
    p.add_argument("--reviewer")
    p.add_argument("--source")
    p.add_argument("--tests")
    a = p.parse_args(argv)
    results = grade(a.repo, a.transcript, a.playbook, a.reviewer, a.source, a.tests)
    for ok, what, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {what}" + (f"  ({detail})" if detail and not ok else ""))
    failed = sum(not ok for ok, _, _ in results)
    print(f"{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
