# Contract: Dirty Repo Check

Added to `repo_analysis_node` after config parsing succeeds.

## Check

```sh
git -C <repo_path> diff --quiet HEAD
git -C <repo_path> ls-files --others --exclude-standard
```

A repo is considered dirty if either:
- `git diff --quiet HEAD` returns non-zero (tracked files modified or staged)
- `git ls-files --others --exclude-standard` returns any output (untracked files present)

## Escalation

| EscalationReason | `DIRTY_REPO` |
|------------------|--------------|
| What happened | "Target repo has uncommitted changes: `<file list>`" |
| What's needed | "Commit, stash, or discard changes in the target repo before running bureau" |
| Options | 1. `git stash` and resume; 2. `git checkout .` to discard; 3. Abort run |

## Notes

- Check runs AFTER config parse succeeds — no point checking if config is missing
- Untracked files from a previous bureau run (builder wrote files but didn't commit) trigger this check, forcing the developer to clean up before the next run
