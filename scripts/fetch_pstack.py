#!/usr/bin/env python3
"""Fetch pstack's Claude Code build at the commit pinned in stack.json.

  fetch_pstack.py [--dest DIR]     prints the path of harness/pstack/claude-code
Default DIR: .cache/cursor-plugins (git-ignored). Idempotent: an existing checkout at
the pinned commit is reused.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def fetch(dest: Path) -> Path:
    pin = json.loads((ROOT / "stack.json").read_text(encoding="utf-8"))["pstack"]
    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        git("init", "-q", cwd=dest)
        git("remote", "add", "origin", pin["repo"], cwd=dest)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=dest, capture_output=True, text=True).stdout.strip()
    if head != pin["commit"]:
        git("fetch", "-q", "--depth", "1", "origin", pin["commit"], cwd=dest)
        git("checkout", "-q", "--detach", pin["commit"], cwd=dest)
    out = dest / pin["path"]
    if not (out / "skills" / "poteto-mode" / "SKILL.md").exists():
        raise SystemExit(f"pinned commit has no pstack build at {pin['path']}")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--dest", type=Path, default=ROOT / ".cache" / "cursor-plugins")
    print(fetch(p.parse_args().dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
