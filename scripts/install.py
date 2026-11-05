#!/usr/bin/env python3
"""Install pstack and iskandar-stack.

  install.py antigravity [--home DIR] [--copy]
      Build pstack for Antigravity (pinned commit) and install both plugins.
      Uses `agy plugin install <dir>` when agy is on PATH, else copies into
      <home>/.gemini/config/plugins/ and enables them in config.json (backed up first).
  install.py claude-project <repo>
      Make Claude Code sessions in <repo> load both plugins: merges
      extraKnownMarketplaces and enabledPlugins into <repo>/.claude/settings.json.
  install.py claude-user
      `claude plugin marketplace add` + `claude plugin install` for this machine's Claude Code.

Every command is idempotent: running it twice leaves the same result.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402
import fetch_pstack  # noqa: E402

META = json.loads((ROOT / "stack.json").read_text(encoding="utf-8"))
MARKETPLACES = {
    "cursor-plugins": {"source": {"source": "github", "repo": "cursor/plugins"}},
    "iskandar-stack": {"source": {"source": "github", "repo": "iskandarnorazli/iskandar-stack"}},
}
PLUGINS = {"pstack@cursor-plugins": True, "iskandar-stack@iskandar-stack": True}


def find_agy():
    for name in ("agy", "agy.exe"):
        p = shutil.which(name)
        if p:
            return p
    local = os.environ.get("LOCALAPPDATA")
    if local and (Path(local) / "agy" / "bin" / "agy.exe").exists():
        return str(Path(local) / "agy" / "bin" / "agy.exe")
    return None


def copy_plugin(src: Path, plugins: Path, name: str) -> Path:
    dest = plugins / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    return dest


def enable_in_config(config: Path, names) -> bool:
    data = json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}
    plugins = data.setdefault("plugins", {})
    changed = False
    for n in names:
        entry = plugins.setdefault(n, {})
        if entry.get("enabled") is not True:
            entry["enabled"] = True
            changed = True
    if changed:
        if config.exists():
            shutil.copy2(config, config.with_suffix(".json.bak-iskandar-stack"))
        config.parent.mkdir(parents=True, exist_ok=True)
        tmp = config.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, config)
    return changed


def install_antigravity(home: Path, force_copy: bool) -> int:
    with tempfile.TemporaryDirectory() as t:
        pstack_src = fetch_pstack.fetch(ROOT / ".cache" / "cursor-plugins")
        pstack_ag = Path(t) / "pstack"
        build.pstack_antigravity(pstack_src, pstack_ag)
        ours = ROOT / "dist" / "antigravity"
        agy = None if force_copy else find_agy()
        if agy:
            for d in (pstack_ag, ours):
                r = subprocess.run([agy, "plugin", "install", str(d)], capture_output=True, text=True)
                print(r.stdout.strip() or r.stderr.strip())
                if r.returncode != 0:
                    print(f"agy plugin install {d.name} failed ({r.returncode}); rerun with --copy", file=sys.stderr)
                    return r.returncode
            return 0
        plugins = home / ".gemini" / "config" / "plugins"
        for src, name in ((pstack_ag, "pstack"), (ours, META["name"])):
            print(f"copied {copy_plugin(src, plugins, name)}")
        changed = enable_in_config(home / ".gemini" / "config" / "config.json", ["pstack", META["name"]])
        print("enabled in config.json" if changed else "already enabled in config.json")
        print("Restart Antigravity (or run /skills reload in the CLI) to load the plugins.")
    return 0


def install_claude_project(repo: Path) -> int:
    p = repo / ".claude" / "settings.json"
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    data.setdefault("extraKnownMarketplaces", {}).update(MARKETPLACES)
    data.setdefault("enabledPlugins", {}).update(PLUGINS)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {p}")
    return 0


def install_claude_user() -> int:
    steps = [["claude", "plugin", "marketplace", "add", "cursor/plugins"],
             ["claude", "plugin", "marketplace", "add", "iskandarnorazli/iskandar-stack"],
             ["claude", "plugin", "install", "pstack@cursor-plugins"],
             ["claude", "plugin", "install", "iskandar-stack@iskandar-stack"]]
    for s in steps:
        r = subprocess.run(s, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        print(f"$ {' '.join(s)}\n{out}")
        if r.returncode != 0 and "already" not in out.lower():
            return r.returncode
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="what", required=True)
    a = sub.add_parser("antigravity")
    a.add_argument("--home", type=Path, default=Path.home())
    a.add_argument("--copy", action="store_true", help="copy files instead of calling agy")
    c = sub.add_parser("claude-project")
    c.add_argument("repo", type=Path)
    sub.add_parser("claude-user")
    args = p.parse_args(argv)
    if args.what == "antigravity":
        return install_antigravity(args.home, args.copy)
    if args.what == "claude-project":
        return install_claude_project(args.repo)
    return install_claude_user()


if __name__ == "__main__":
    sys.exit(main())
