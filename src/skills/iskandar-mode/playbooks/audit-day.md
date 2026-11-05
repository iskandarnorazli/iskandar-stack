### Audit day

**You own an independent verdict on the other agent's batch, and a full queue for its next run.** Use the project's own audit steps when it has them (awan-lang: `CLAUDE.md`, "Cadence"); these steps fill the gaps.

1. List the batch: branches not yet merged into the integration branch, open tasks in `state.py status --owner <other agent>`, and issues labelled for review. Open a task state for the audit itself.
2. Per branch, in a separate worktree when another agent is active:
   - Diff against the issue's gate. Every gate line is met as written, or it is a finding.
   - No test weakened, skipped or deleted: `git diff --stat` over the test folders, and read each changed assertion.
   - Negative control: revert the fix, run the new test, see it fail.
   - The commit message carries the evidence; a measurement carries its command.
   - Both platforms: the project's CI jobs, or its substitute.
   Log one decision row per branch: merged, fixed in a follow-up commit, or sent back with the reason.
3. Fix small problems in a follow-up commit. Send larger ones back in an issue comment with the failing command and its output.
4. Merge what passes into the integration branch and run the full suite once. Ask the owner to push once.
5. Close issues only with gate evidence in the closing comment, and only as the reviewer, never as the builder.
6. Refill the queue: about ten issues that meet the Definition of Ready (step 2 of the Handoff playbook), outside the project's risky areas. An empty queue sends the other agent to work that is not ready.
7. Look for repeats. A mistake class seen twice goes to pstack's **correct** skill: fix it in structure (a check, a test, a lint) rather than another rule.

**Reply:** the table of branches with verdicts and evidence, what merged, what went back and why, the suite result, the queue size, and the one push the owner needs to make.
