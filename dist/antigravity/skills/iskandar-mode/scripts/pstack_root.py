#!/usr/bin/env python3
"""Print the folder that holds pstack's skills/ (the one with skills/poteto-mode/SKILL.md).

Order: $PSTACK_ROOT, then each harness's plugin folders. With several copies, the
highest plugin.json version wins. Exit 1 when pstack is not installed.
"""
import json
import os
import sys
from pathlib import Path

MARK = Path("skills") / "poteto-mode" / "SKILL.md"


def candidates(home: Path):
    env = os.environ.get("PSTACK_ROOT")
    if env:
        yield Path(env)
    for base in (
        home / ".claude" / "plugins",            # Claude Code (marketplace cache)
        home / ".gemini" / "config" / "plugins",  # Antigravity
        home / ".cursor" / "plugins",             # Cursor
    ):
        if base.is_dir():
            for mark in base.rglob("poteto-mode/SKILL.md"):
                if mark.parent.parent.name == "skills":
                    yield mark.parent.parent.parent


def version(root: Path):
    for rel in ("plugin.json", ".claude-plugin/plugin.json", ".cursor-plugin/plugin.json", ".antigravity-plugin/plugin.json"):
        p = root / rel
        if p.exists():
            try:
                v = json.loads(p.read_text(encoding="utf-8")).get("version", "0")
                return tuple(int(x) if x.isdigit() else 0 for x in str(v).split("."))
            except (ValueError, OSError):
                pass
    return (0,)


def find(home: Path):
    found = [c for c in candidates(home) if (c / MARK).exists()]
    if os.environ.get("PSTACK_ROOT") and found and found[0] == Path(os.environ["PSTACK_ROOT"]):
        return found[0]
    return max(found, key=version) if found else None


def main() -> int:
    root = find(Path(os.environ.get("ISKANDAR_HOME") or Path.home()))
    if root is None:
        print("pstack not found: install it (see iskandar-stack README) or set PSTACK_ROOT", file=sys.stderr)
        return 1
    print(root.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
