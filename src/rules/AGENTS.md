# iskandar-stack

- Shared task state lives in `.agents/state/<id>/` of the repository. At the start of work in a repository, run the **task-state** skill's `state.py status`. A task whose owner is `antigravity` is yours to resume with `state.py resume <id> --run <conversation id>`; read its Handoff first and do not redo verified work.
- Keep the task state in step with your artifacts: copy the implementation plan with `state.py plan`, the task list with `state.py task`, and the walkthrough with `state.py walkthrough`. Claude reads the state, not your artifacts.
- Never move a task you built to `done`. Hand it to Claude or the owner for review.
- When the owner says `/iskandar-mode` or asks you to work in Iskandar's style, follow the **iskandar-mode** skill. Map pstack's Cursor names with this plugin's `docs/harness/antigravity.md`.
