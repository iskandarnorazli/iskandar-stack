#!/usr/bin/env python3
"""Make the seeded-bug repository the workflow runs are graded on.

  make_scenario.py <dir>                  a fresh repo: clamp() returns lo above hi
  make_scenario.py <dir> --from-run <repo> copy a finished run (git history and .agents/state)

The prompt for every run, either agent:
  /iskandar-mode Users report clamp(15, 0, 10) returns 0 instead of 10. Fix it.
  When it is ready for review, hand it to <the other agent> for the review; do not review it yourself.
Grade with: check_run.py <dir> --playbook bug-fix --reviewer <other> --source calc.py --tests test_calc.py
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

CALC = '''def clamp(x, lo, hi):
    """Return x limited to the range [lo, hi]."""
    if x < lo:
        return lo
    if x > hi:
        return lo
    return x
'''
TEST = '''import unittest
from calc import clamp

class ClampTest(unittest.TestCase):
    def test_inside(self):
        self.assertEqual(clamp(5, 0, 10), 5)

if __name__ == "__main__":
    unittest.main()
'''


def git(d, *a):
    subprocess.run(["git", "-c", "user.name=scenario", "-c", "user.email=scenario@example.invalid", *a],
                   cwd=d, check=True, capture_output=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("dir", type=Path)
    p.add_argument("--from-run", type=Path)
    a = p.parse_args()
    if a.dir.exists():
        print(f"{a.dir} exists", file=sys.stderr)
        return 1
    if a.from_run:
        shutil.copytree(a.from_run, a.dir, ignore=shutil.ignore_patterns("__pycache__"))
        print(a.dir)
        return 0
    a.dir.mkdir(parents=True)
    (a.dir / "calc.py").write_text(CALC, encoding="utf-8")
    (a.dir / "test_calc.py").write_text(TEST, encoding="utf-8")
    (a.dir / ".gitignore").write_text(".agents/state/\n__pycache__/\n", encoding="utf-8")
    git(a.dir, "init", "-q", "-b", "main")
    git(a.dir, "add", "-A")
    git(a.dir, "commit", "-qm", "init")
    print(a.dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
