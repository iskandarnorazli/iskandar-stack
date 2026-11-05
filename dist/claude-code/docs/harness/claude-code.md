# iskandar-stack in Claude Code

pstack ships its own Claude Code adapter at `<pstack>/docs/harness/claude-code.md`. Read it once per session; it maps pstack's Cursor names. This file adds only what iskandar-stack changes.

| pstack or Cursor | Claude Code with iskandar-stack |
| --- | --- |
| `poteto-agent` | `iskandar-stack:iskandar-agent`. Put the path of `iskandar-mode/SKILL.md` in the prompt. |
| Open a todolist | `TaskCreate` / `TaskUpdate` when the session has them, else `TodoWrite`. Keep the same items in the shared state (`state.py task <id> add ...`), which is what Antigravity reads. |
| show-me-your-work's `decisions.tsv` | The task's `DECISIONS.tsv` (`state.py log`). Same columns, same `start` rows. |
| Pause safely's resume note | `state.py phase <id> paused --reason ... --next ...`. The note lives in the task's Handoff, not in `/tmp`. |
| Session pickup | `state.py status`, then `state.py resume <id> --run <session id>`. |
| A Claude cloud session (claude.ai) | Plugins come from the repo's `.claude/settings.json` (`extraKnownMarketplaces`, `enabledPlugins`). A session started outside the repo does not load them; read the skill files by path instead. |

Find pstack with `python3 <iskandar-stack>/skills/iskandar-mode/scripts/pstack_root.py`.
