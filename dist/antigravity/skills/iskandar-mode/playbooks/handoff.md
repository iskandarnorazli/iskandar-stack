### Handoff

**You own a handoff the other agent can finish without asking.** It works in both directions: Claude to Antigravity, Antigravity to Claude, either to the owner.

1. Open or update the task state (the **task-state** skill). The Goal is the owner's goal in their words.
2. Write the task to a Definition of Ready. Use the project's issue-writing skill if it has one; otherwise the Plan must hold all of these:
   - the goal as an observable behaviour;
   - the invariants, each with the test that checks it;
   - the decisions already made, with where they are recorded;
   - the files in scope and the files and behaviours that must not change;
   - the steps as constraints, not a mechanism, unless a mechanism was decided;
   - the gate, as commands with their expected output and where the evidence goes;
   - the stop conditions: a language rule change, a test expectation change, a file outside the list, or a gate that cannot be met as written.
3. Check that no other agent holds the work: the project's claim labels (`wip:claude`, `wip:antigravity`) and `state.py status`. Claim it for the receiver.
4. A handoff for review needs the task in `review`: tasks closed, Walkthrough written, `phase review` run. The script refuses it otherwise.
5. Hand off: `state.py handoff <id> --to <agent> --for <plan|build|review|decide> --next "<first action>" --files "<key files>" --questions "<open questions, or none>"`. Point the receiver at the state folder, not at the conversation.
   - To Antigravity in the desktop app: give the owner one line to paste: `Use /iskandar-mode. Resume .agents/state/<id>/`.
   - To Antigravity through a print-mode runner: write the task file the runner reads with the same content, and name the report path.
   - To Claude: the same line. Claude runs `state.py resume <id> --run <session>`.
6. The receiver runs `state.py resume`, reads STATE.md and the last rows of DECISIONS.tsv, and continues from the Handoff's Next. It does not redo verified work (pstack's **Session pickup** playbook).
7. On return, verify before you trust. Read the diff, rerun the gate commands yourself, and revert the fix once to see the new test fail. A report that claims a change the tree does not have is a finding: log it.
8. The reviewer, never the builder, moves the task to `done` (`--by <reviewer>`).

**Reply:** who holds the task now, the state id, the first action the receiver takes, and anything the owner must decide before it can start.
