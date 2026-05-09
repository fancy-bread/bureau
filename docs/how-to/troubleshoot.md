---
icon: octicons/bug-24
---

# Troubleshoot

---

## Escalation reasons

When bureau pauses, the `run.escalated` event includes a `reason` field. Each reason has a specific fix.

| Reason | Cause | Fix |
|---|---|---|
| `SPEC_INVALID` | Missing P1 stories, `[NEEDS CLARIFICATION]` markers, or unparseable spec | Fix `spec.md` and re-run |
| `CONFIG_MISSING` | `.bureau/config.toml` not found in target repo | Run `bureau init --repo <path>` |
| `TASKS_MISSING` | `tasks.md` not found in spec folder | Run `/speckit-tasks` in Claude Code |
| `DIRTY_REPO` | Target repo has uncommitted changes before `prepare_branch` | Commit or stash changes, then resume |
| `GIT_BRANCH_EXISTS` | Feature branch already exists in the repo | Delete the branch and resume, or use a fresh run |
| `GIT_PUSH_FAILED` | Branch push to remote failed | Check remote access and `gh auth status`, then resume |
| `PR_FAILED` | `gh pr create` failed | Check `gh auth status` and remote permissions, then resume |
| `RALPH_EXHAUSTED` | Builder failed after `max_builder_attempts` within a round | Review test output in escalation; fix spec or resume |
| `RALPH_ROUNDS_EXCEEDED` | Reviewer returned `revise` after `max_rounds` full cycles | Unmet FRs listed in escalation; clarify spec and resume |
| `CONSTITUTION_VIOLATION` | Reviewer found a CRITICAL finding against the constitution | Resolve the violation; may require spec or constitution update |
| `BLOCKER` | Builder hit an unresolvable ambiguity mid-implementation | Provide missing context via `bureau resume --response "..."` |

---

## Resuming after an escalation

```sh
bureau list --status paused        # find the run ID
bureau show <run-id>               # read the escalation detail
bureau resume <run-id>             # resume after fixing the root cause
```

Run state is fully checkpointed. Bureau resumes from the node that escalated, not from the beginning.

---

## Inspecting run files

Each run stores its state in `~/.bureau/runs/<run-id>/`:

```
~/.bureau/runs/run-a3f9c2b1/
├── run.json           ← run record: status, phase, timestamps
├── checkpoint.db      ← LangGraph SQLite checkpoint (full node state)
├── memory.json        ← inter-phase scratchpad
└── run-summary.json   ← terminal summary (written at pass/escalate/fail)
```

`run.json` is the first place to check — it shows the current phase and status. `run-summary.json` exists only after the run has terminated.

---

## Common issues

**`ANTHROPIC_API_KEY` not set**

```
[bureau] error: ANTHROPIC_API_KEY not set — add it to ~/.bureau/.env or export it in your shell
```

Add the key to `~/.bureau/.env` or export it in your shell. See [Installation](../getting-started/installation.md).

---

**`gh` not authenticated**

```
[bureau] run.escalated  reason=PR_FAILED
```

Run `gh auth status` to verify. If not authenticated, run `gh auth login`.

---

**Tests pass locally but Reviewer returns `revise`**

The Reviewer re-runs the test suite independently against the committed branch. Check that all Builder phase-end commits were pushed (`git log --oneline`) and that the test suite is deterministic. Flaky tests will cause the Reviewer to return `revise` even when the Builder saw a pass.

---

**Run stuck / appears hung**

Check if a bureau process is still active:

```sh
ps aux | grep bureau
```

If no process is running, the run likely failed silently. Check `~/.bureau/runs/<run-id>/run.json` for the last recorded phase, then `bureau resume <run-id>` to continue from the checkpoint.
