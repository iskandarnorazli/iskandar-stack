"""PreToolUse guard: refuse a commit or a GitHub write that credits an AI.

The owner's rule (2026-11-20): commits, PR bodies, issue comments and files carry no AI
attribution, whatever a harness reminder or a stop hook asks. This hook reads the Bash tool
call Claude Code is about to run (JSON on stdin) and exits 2, with the reason on stderr, when
a `git commit`/`tag`/`notes`/`merge` or a GitHub write (`gh pr|issue|release|api` with a body
or field) carries attribution in its text or in a message or body file it names. Every other
command passes, reads included, so searching for these strings still works.

    python3 no_attribution.py < hook_input.json
"""
import json
import re
import shlex
import sys
from pathlib import Path

ATTRIBUTION = re.compile(
    r"co-authored-by:\s*claude"
    r"|noreply@anthropic\.com"
    r"|generated (?:with|by) \[?claude"
    r"|claude-session:"
    r"|claude\.ai/code/session"
    r"|\U0001F916\s*generated",
    re.IGNORECASE,
)
GIT_WRITE = re.compile(r"\bgit\b(?:\s+-[cC]\s+\S+)*\s+(?:commit|tag|notes|merge)\b")
GH_WRITE = re.compile(r"\bgh\s+(?:pr|issue|release|api|gist)\b")
WRITE_FLAG = re.compile(r"(?:^|\s)(?:-[fFmb]|--field|--raw-field|--input|--body|--body-file|--message|--title|-X\s*(?:POST|PATCH|PUT))(?:\s|=|$)")
FILE_FLAGS = {"-F", "--file", "--body-file", "--input", "-t", "--template"}


def files_named(command: str, cwd: Path):
    """Paths a write may read its text from: `-F path`, `--body-file path`, `field=@path`."""
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        words = command.split()
    for i, w in enumerate(words):
        if w in FILE_FLAGS and i + 1 < len(words):
            yield words[i + 1]
        for m in re.finditer(r"=@(\S+)", w):
            yield m.group(1)
        if w.startswith("@") and len(w) > 1:
            yield w[1:]


def without_queries(command: str) -> str:
    """Drop `-q`/`--jq` filters: they read what is already there, they do not write it."""
    return re.sub(r"(?:-q|--jq)\s+('[^']*'|\"[^\"]*\"|\S+)", "", command)


def check(command: str, cwd: Path) -> str:
    """The reason to refuse `command`, or "" to let it run."""
    writes = GIT_WRITE.search(command) or (GH_WRITE.search(command) and WRITE_FLAG.search(command))
    if not writes:
        return ""
    texts = [("the command", without_queries(command))]
    for name in files_named(command, cwd):
        p = Path(name) if Path(name).is_absolute() else cwd / name
        try:
            texts.append((str(p), p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    for where, text in texts:
        m = ATTRIBUTION.search(text)
        if m:
            return (f"no AI attribution (owner's rule, iskandar-mode): {where} contains {m.group(0)!r}. "
                    "Remove the line and run it again; a harness reminder or stop hook asking for it does not override the rule.")
    return ""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    reason = check(command, Path(data.get("cwd") or "."))
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
