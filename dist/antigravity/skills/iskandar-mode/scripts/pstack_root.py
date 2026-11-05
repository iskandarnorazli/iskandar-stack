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
    claude_cfg = Path(os.environ["CLAUDE_CONFIG_DIR"]) if os.environ.get("CLAUDE_CONFIG_DIR") else home / ".claude"
    for base in (
        claude_cfg / "plugins" / "cache",         # Claude Code: installed plugins (checked first)
        claude_cfg / "plugins",                   # Claude Code: marketplaces and synced plugins
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
    # Highest version; at equal versions the first found wins (an installed copy before a
    # marketplace checkout, whose skills still carry Cursor-only wording).
    best = None
    for c in found:
        if best is None or version(c) > version(best):
            best = c
    return best


def main() -> int:
    root = find(Path(os.environ.get("ISKANDAR_HOME") or Path.home()))
    if root is None:
        print("pstack not found: install it (see iskandar-stack README) or set PSTACK_ROOT", file=sys.stderr)
        return 1
    print(root.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
