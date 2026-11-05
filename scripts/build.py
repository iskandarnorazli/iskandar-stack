#!/usr/bin/env python3
"""Build the harness plugins from src/.

  build.py                      write dist/claude-code and dist/antigravity
  build.py --check              exit 1 if dist/ differs from a fresh build
  build.py pstack-antigravity --src <cursor-plugins>/harness/pstack/claude-code --out <dir>
                                make an Antigravity build of pstack from its Claude Code build

Both harnesses read SKILL.md the same way; they differ in the plugin manifest,
agent frontmatter (Antigravity needs an explicit tools list), rules and hooks.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = json.loads((ROOT / "stack.json").read_text(encoding="utf-8"))

# Antigravity 2.0 tool names seen in the owner's transcripts (docs/harness/antigravity.md).
# An unknown name in an agent's tools list can hang that agent, so this list is closed.
ANTIGRAVITY_TOOLS = [
    "view_file", "read_file", "grep_search", "find_by_name", "list_dir",
    "write_to_file", "write_file", "replace_file_content", "edit_file",
    "run_command", "manage_task", "call_mcp_tool", "send_message",
]
ADAPTER_LINE = ("In Claude Code, read [the Claude Code adapter](../../docs/harness/claude-code.md) "
                "once per session before you follow this skill. It maps the Cursor names in pstack skills to Claude Code.")
ANTIGRAVITY_ADAPTER = "~/.gemini/config/plugins/iskandar-stack/docs/harness/antigravity.md"


def split_frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text.replace("\r\n", "\n"), re.S)
    if not m:
        raise ValueError("no frontmatter")
    fields = {}
    for line in m.group(1).split("\n"):
        k, _, v = line.partition(":")
        if k.strip():
            fields[k.strip()] = v.strip()
    return fields, m.group(2)


def agent_for(harness: str, text: str) -> str:
    fields, body = split_frontmatter(text)
    desc = fields["description"]
    if not (desc.startswith('"') and desc.endswith('"')):
        desc = json.dumps(desc)  # a JSON string is a valid YAML double-quoted scalar
    keep = {"name": fields["name"], "description": desc}
    lines = [f"{k}: {v}" for k, v in keep.items()]
    if harness == "antigravity":
        lines.append("tools: [" + ", ".join(ANTIGRAVITY_TOOLS) + "]")
        lines.append("model: inherit")
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def manifest(harness: str) -> dict:
    m = {
        "name": META["name"],
        "version": META["version"],
        "description": META["description"],
        "author": META["author"],
        "license": META["license"],
        "repository": META["repository"],
    }
    if harness == "antigravity":
        m["displayName"] = META["displayName"]
    return m


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    for harness in ("claude-code", "antigravity"):
        d = out / harness
        shutil.copytree(ROOT / "src" / "skills", d / "skills", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(ROOT / "docs" / "harness", d / "docs" / "harness")
        shutil.copy2(ROOT / "LICENSE", d / "LICENSE")
        for a in sorted((ROOT / "src" / "agents").glob("*.md")):
            write(d / "agents" / a.name, agent_for(harness, a.read_text(encoding="utf-8")))
        man = json.dumps(manifest(harness), indent=2) + "\n"
        if harness == "claude-code":
            write(d / ".claude-plugin" / "plugin.json", man)
            hooks = {"hooks": {"SessionStart": [{"hooks": [{
                "type": "command",
                "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/skills/task-state/scripts/state.py\" status --brief --quiet || true",
            }]}]}}
            write(d / "hooks" / "hooks.json", json.dumps(hooks, indent=2) + "\n")
        else:
            write(d / "plugin.json", man)
            shutil.copytree(ROOT / "src" / "rules", d / "rules")


def same_tree(a: Path, b: Path) -> list:
    diffs = []
    cmp = filecmp.dircmp(a, b, ignore=["__pycache__"])

    def walk(c, rel):
        diffs.extend(f"{rel}{n}: only in {Path(c.left).name}/" for n in c.left_only)
        diffs.extend(f"{rel}{n}: only in fresh build" for n in c.right_only)
        for n in c.common_files:
            if (Path(c.left) / n).read_bytes() != (Path(c.right) / n).read_bytes():
                diffs.append(f"{rel}{n}: differs")
        for n, sub in c.subdirs.items():
            walk(sub, f"{rel}{n}/")
    walk(cmp, "")
    return diffs


def pstack_antigravity(src: Path, out: Path) -> int:
    """Antigravity build of pstack: same skills, an Antigravity adapter line, converted agents."""
    if not (src / "skills" / "poteto-mode" / "SKILL.md").exists():
        print(f"not a pstack build: {src}", file=sys.stderr)
        return 1
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns(".claude-plugin", ".cursor-plugin"))
    patched = 0
    for p in (out / "skills").glob("*/SKILL.md"):
        t = p.read_text(encoding="utf-8")
        if ADAPTER_LINE in t:
            t = t.replace(ADAPTER_LINE, ADAPTER_LINE + f" In Antigravity, read `{ANTIGRAVITY_ADAPTER}` instead.")
            p.write_text(t, encoding="utf-8", newline="\n")
            patched += 1
    for a in (out / "agents").glob("*.md"):
        t = agent_for("antigravity", a.read_text(encoding="utf-8"))
        t = t.replace("search `~/.cursor/plugins/`", "search `~/.gemini/config/plugins/` (Antigravity) or `~/.cursor/plugins/`")
        a.write_text(t, encoding="utf-8", newline="\n")
    pj = out / "plugin.json"
    data = json.loads(pj.read_text(encoding="utf-8"))
    data.setdefault("displayName", "pstack")
    pj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"pstack for Antigravity: {out} ({patched} skills point at the Antigravity adapter)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("what", nargs="?", default="stack", choices=("stack", "pstack-antigravity"))
    p.add_argument("--check", action="store_true")
    p.add_argument("--src", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    if a.what == "pstack-antigravity":
        if not a.src or not a.out:
            p.error("pstack-antigravity needs --src and --out")
        return pstack_antigravity(a.src, a.out)
    if a.check:
        with tempfile.TemporaryDirectory() as t:
            fresh = Path(t) / "dist"
            build(fresh)
            diffs = same_tree(ROOT / "dist", fresh) if (ROOT / "dist").exists() else ["dist/ missing"]
        for d in diffs:
            print(d)
        if diffs:
            print("dist/ is stale: run python3 scripts/build.py", file=sys.stderr)
        return 1 if diffs else 0
    build(ROOT / "dist")
    print(f"built {ROOT / 'dist'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
