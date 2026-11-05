# iskandar-stack

Iskandar's agent workflow, one source for Claude Code and Antigravity 2.0.

- **iskandar-mode** routes work through [pstack](https://github.com/cursor/plugins/tree/main/pstack) (Lauren Tan's playbooks, principles and workflow skills) and adds the owner's rules: evidence before claims, tests that catch the bug, the owner decides language and scope, the builder never closes its own work.
- **task-state** keeps one folder per task in `.agents/state/<id>/` that either agent resumes from: goal, plan (Antigravity's shape), tasks, handoff, walkthrough, an append-only decision log (pstack's show-me-your-work format), and a Mermaid chart of the lifecycle redrawn on every change.
- **Handoff** and **Audit day** playbooks move work between Claude and Antigravity.
- Harness adapters map pstack's Cursor names to each agent's tools: `docs/harness/antigravity.md` (from Antigravity 2.0's own transcripts) and `docs/harness/claude-code.md`.

## Install

Antigravity (desktop app and `agy` CLI), on the machine that runs it:

```sh
python scripts/install.py antigravity          # uses `agy plugin install` when agy is on PATH
python scripts/install.py antigravity --copy   # copies into ~/.gemini/config/plugins and enables them
```

Claude Code, for every session in a repository (cloud sessions included):

```sh
python3 scripts/install.py claude-project /path/to/repo   # writes .claude/settings.json
```

Claude Code on one machine: `python3 scripts/install.py claude-user`.

Both install pstack too: Claude Code from the `cursor/plugins` marketplace, Antigravity from pstack's Claude Code build at the commit pinned in `stack.json`, converted by `scripts/build.py pstack-antigravity`.

## Use

- Claude Code: `/iskandar-stack:iskandar-mode <task>`.
- Antigravity: `/iskandar-mode <task>`.
- Pick up the other agent's work: `Use /iskandar-mode. Resume .agents/state/<id>/`.

## Develop

```sh
python3 scripts/fetch_pstack.py        # pinned pstack into .cache/ (for the coverage tests)
python3 scripts/build.py               # src/ -> dist/claude-code, dist/antigravity
python3 -m unittest discover -s tests  # state CLI, builds, adapters, installers
```

`dist/` is committed so both harnesses can install from GitHub; a test fails when it is stale. Edit `src/`, never `dist/`.
