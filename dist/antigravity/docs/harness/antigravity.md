# pstack and iskandar-stack in Antigravity 2.0

pstack skills use Cursor names. In Antigravity, read this file once per session, then map each Cursor name with the tables below. `<pstack>` means the folder that holds pstack's `skills/` (`python <iskandar-stack>/skills/iskandar-mode/scripts/pstack_root.py` prints it). If a Cursor field has no row, drop it and say so.

pstack's Claude Code build says "In Claude Code, read the Claude Code adapter". In Antigravity, read this file instead.

The tool names below come from Antigravity 2.0 transcripts on the owner's laptop (60 sessions, 2026-11-05). `tests/test_adapters.py` keeps this table covering every Cursor name pstack's own Claude Code adapter maps.

## Tools

| Cursor | Antigravity 2.0 |
| --- | --- |
| `Task` | `invoke_subagent` with `TypeName` (a custom agent name, or a built-in such as `research` or a teamwork role), `Role`, `Prompt`, `Model`, `Workspace`. Poll with `manage_subagents` (`Action: list`); stop with `kill`. |
| `AskQuestion` | `ask_question` in the desktop app. In CLI print mode (`agy -p`, the runner) a question is denied: write the question in the reply and stop. |
| Open a todolist | Keep the task list in the shared state: `state.py task <id> add ...` (the **task-state** skill). Also write it as a `task.md` artifact with `write_file` and `ArtifactMetadata: {Summary, UserFacing: true, RequestFeedback: false}` so the owner sees it in Agent Manager. The state file is the one other agents read. |
| Run another pstack skill (`/name` or "the **name** skill") | `view_file` `<pstack>/skills/<name>/SKILL.md` and follow it. In the desktop app the owner can type `/<name>`. |
| `Read` | `view_file` (`AbsolutePath`, `StartLine`, `EndLine`) or `read_file`. |
| `Grep`, `Glob` | `grep_search`, `find_by_name`, `list_dir`. |
| `Edit` | `replace_file_content` (`TargetFile`, `TargetContent`, `ReplacementContent`) or `edit_file`. |
| `Write` | `write_to_file` (`TargetFile`, `CodeContent`), or `write_file` for an artifact. |
| `Shell` | `run_command` (`CommandLine`, `WaitMsBeforeAsync`). A long command runs async: check it with `manage_task` (`Action: status`, `TaskId`). `manage_task` tracks commands; it is not a to-do list. |
| `/loop`, a wake-up later | `schedule` (`DurationSeconds` or `CronExpression`, `Prompt`). |
| An MCP tool | `call_mcp_tool` (`ServerName`, `ToolName`, `Arguments`). In print mode each tool needs an allow rule in the owner's settings, or the run aborts. |
| Message a running subagent | `send_message` (`Recipient`, `Message`). |

## Plans and approvals

pstack's "show the plan" and Antigravity's implementation plan are one artifact. Write the plan in Antigravity's shape (Goal, User Review Required, Open Questions, Proposed Changes per file with `[NEW]`, `[MODIFY]` or `[DELETE]`, Verification Plan) with `write_file`, `ArtifactMetadata.RequestFeedback: true` when the owner must approve, and copy it into the task's Plan with `state.py plan <id> --file <artifact>`. The walkthrough works the same way: write the artifact, then `state.py walkthrough <id> --file <artifact>`.

## Subagent fields

| Cursor | Antigravity 2.0 |
| --- | --- |
| `subagent_type: generalPurpose` | `TypeName: self` (a clone of you), or a custom agent. |
| `poteto-agent` | `TypeName: iskandar-agent` (installed by iskandar-stack). Put the path of `iskandar-mode/SKILL.md` in the prompt. |
| `comment-sicko` | `TypeName: comment-sicko` (installed by iskandar-stack's Antigravity build). |
| `readonly: true` | `TypeName: research`, or say "do not edit files" in the prompt and check `git status` afterwards. |
| `readonly: false` | Any agent with edit tools. |
| `environment: "cloud"`, `isolation: "worktree"` | `Workspace: branch` (its own git worktree). Name the branch it starts from. |
| `environment: "local"` | `Workspace: inherit`. |
| `cloud_base_branch: <b>` | Tell the agent to check out `<b>` first (with `Workspace: branch`). |
| `run_in_background: true` | Omit. Subagents run concurrently; poll `manage_subagents`. |
| `resume` | `send_message` to the running agent, or a fresh `invoke_subagent` with the earlier result in the prompt. |
| `file_attachments` | List the paths in the prompt. |
| A swarm, arena or gauntlet | The owner's `/teamwork` when it is running: keep its roles (`teamwork_interviewer`, `teamwork_explorer`, `teamwork_worker`, `teamwork_reviewer`, `teamwork_challenger`, `teamwork_auditor`, `teamwork_victory_auditor`) and do not swap in pstack's swarm. The challenger runs only where iskandar-mode's risk rule calls for adversarial review. Brief each role with `state.py agent <id> <role> --text ...` so its BRIEFING, progress and handoff land in the shared state. |

## Models

| Cursor | Antigravity 2.0 |
| --- | --- |
| `claude-opus-*-xhigh`, any "strongest judgment" slug | `Model: pro` |
| A fast code slug (`grok-*-fast`, `*-fast`) | `Model: flash` |
| `auto`, `inherit-parent` | `Model: inherit` |
| `~/.cursor/rules/pstack-models.mdc` | No file. Use the defaults above. |

## Paths

| Cursor | Antigravity 2.0 |
| --- | --- |
| `.cursor/skills/`, `~/.cursor/skills/` | `.agents/skills/`, `~/.gemini/config/skills/` |
| `~/.cursor/plugins/`, `.cursor-plugin/plugin.json` | `~/.gemini/config/plugins/` (`agy plugin install <path>`); the manifest is `plugin.json` or `.antigravity-plugin/plugin.json` at the plugin root |
| `.cursor/rules/*.mdc`, always-applied rules | The workspace `AGENTS.md` (`.agents/AGENTS.md` in repos that keep it there), or a plugin's `rules/AGENTS.md`. |
| Custom agents | `.agents/agents/<name>.md`, `~/.gemini/config/agents/<name>.md`, or a plugin's `agents/`. Frontmatter: `name`, `description`, `tools` (a list of the tool names above; an unknown name can hang the agent), `model` (`inherit`, `flash`, `pro`). |
| Transcripts in `~/.cursor/projects/<slug>/agent-transcripts/` | `~/.gemini/antigravity/brain/<conversation>/.system_generated/logs/transcript.jsonl` (desktop app) or `~/.gemini/antigravity-cli/brain/...` (CLI). Read only conversations about the current workspace: the first message names the working directory. |
| `https://github.com/cursor/plugins/blob/main/pstack/<path>` | `<pstack>/<path>` when that file exists. |

## Cursor-only features

Antigravity has no Cursor Automations, Bugbot or Cursor cloud agents. When a step needs one, put one line in your reply, `Skipped in Antigravity: <step>. <reason>.`, and go on. A PR step uses `gh` through `run_command`; that is not a skip.

## Print mode (the runner)

`agy -p` denies every tool that would ask for approval and then exits 0 with "no output produced". A task file for print mode lists only commands the owner's `permissions.allow` rules cover, says "no git", and names the report file. Claude checks the tree, not the report.
