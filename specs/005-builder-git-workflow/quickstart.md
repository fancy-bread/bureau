# Quickstart: Builder Git Workflow

## Happy path

```sh
# bureau-test is clean on main
cd ~/projects/software/bureau-test
git status  # should show: nothing to commit

# run bureau
bureau run specs/001-smoke-hello-world/spec.md --repo .

# expected output includes:
# [bureau] phase.started  phase=git_commit
# [bureau] phase.completed  phase=git_commit  duration=Xs
# [bureau] run.completed  pr=https://github.com/fancy-bread/bureau-test/pull/N  duration=Xs

# verify branch and PR exist
gh pr list
git branch -r | grep feat/
```

## Dirty repo escalation

```sh
# leave a file in bureau-test
echo "dirty" > bureau-test/dirty.txt

bureau run specs/001-smoke-hello-world/spec.md --repo bureau-test/

# expected:
# [bureau] run.escalated  id=...  phase=repo_analysis  reason=DIRTY_REPO
#   What happened:  Target repo has uncommitted changes: dirty.txt
#   What's needed:  Commit, stash, or discard changes before running bureau.

# clean up and resume or re-run
rm bureau-test/dirty.txt
bureau run specs/001-smoke-hello-world/spec.md --repo bureau-test/
```

## Branch collision (simulated)

```sh
# manually create the branch bureau would use
git -C bureau-test checkout -b feat/smoke-hello-world-deaaf184
git -C bureau-test push origin feat/smoke-hello-world-deaaf184
git -C bureau-test checkout main

# bureau will try feat/smoke-hello-world-deaaf184, then -2, then -3
# in practice the run_id differs each run so collisions are rare
```

## Files changed by this feature

| File | Change |
|------|--------|
| `bureau/nodes/git_commit.py` | New node |
| `bureau/nodes/repo_analysis.py` | Add dirty repo check after config parse |
| `bureau/graph.py` | Wire git_commit between critic pass and pr_create |
| `bureau/state.py` | Add Phase.GIT_COMMIT, EscalationReason.DIRTY_REPO/GIT_PUSH_FAILED/GIT_BRANCH_EXISTS, branch_name to initial state |
| `bureau/nodes/pr_create.py` | Read branch_name from state instead of computing it |
| `tests/unit/test_git_commit_node.py` | New unit tests |
| `tests/integration/test_graph_run.py` | Add dirty repo integration test |
