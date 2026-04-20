# Research: Builder Git Workflow

**Feature**: 005-builder-git-workflow
**Date**: 2026-04-19

---

## Decision 1: Where does the git workflow node live?

**Decision**: Dedicated `git_commit` node inserted between Critic `verdict=pass` and `pr_create`.

**Rationale**: Each node in the LangGraph pipeline has a single contract. Builder's contract is "make tests pass." PR create's contract is "open a PR." Git operations (branch, stage, commit, push) are a distinct step with their own failure modes and escalation path. A dedicated node:
- Is independently resumable (checkpointed after critic pass, before git ops)
- Has a clean escalation path that identifies git failures separately from build or PR failures
- Does not require modifying Builder or PR create node logic

**Alternatives considered**:
- End of `builder_node`: Builder is already complex (Ralph loop, install, test iterations). Adding git ops there mixes concerns and means git runs before Critic review — a waste if Critic sends back.
- Start of `pr_create_node`: PR create already exists and works. Splitting its responsibilities increases the blast radius of changes.

---

## Decision 2: Dirty repo check placement

**Decision**: Add dirty repo check to `repo_analysis_node`, which already reads `.bureau/config.toml` and produces `RepoContext`.

**Rationale**: Earliest possible gate. If the repo is dirty, there's no point running Planner or Builder. The check is a one-liner (`git status --porcelain`) and the escalation reason `DIRTY_REPO` is unambiguous.

**Alternatives considered**:
- New `preflight` node: unnecessary indirection for a single check that fits naturally in repo_analysis.

---

## Decision 3: Branch naming convention

**Decision**: `feat/<spec-name>-<run-id-prefix>` where `spec-name` is the stem of the spec file path, lowercased and kebab-cased (non-alphanumeric chars replaced with `-`), and `run-id-prefix` is the first 8 chars of the run ID (which already has a `run-` prefix stripped).

**Example**: spec path `specs/001-smoke-hello-world/spec.md`, run ID `run-deaaf184` → branch `feat/smoke-hello-world-deaaf184`

**Rationale**: Conventional commit prefix (`feat/`) is readable and aligns with standard GitHub branch conventions. Run ID suffix ensures uniqueness across runs for the same spec. Spec name provides human readability at a glance in GitHub.

**Alternatives considered**:
- `bureau/<run-id>`: Original proposal; less readable, non-standard prefix.
- `feat/<run-id>` only: Loses spec name context when browsing branch list.

---

## Decision 4: Git implementation approach

**Decision**: `subprocess.run` calling `git` CLI commands directly. No Python git library.

**Rationale**: `git` CLI is already assumed present (same assumption as `gh` CLI). `subprocess` is stdlib. Adding `pygit2` or `gitpython` would be a new dependency for functionality that four shell commands cover. The git operations required (checkout -b, add, commit, push) are simple and stable.

**Commands**:
```sh
git -C <repo_path> diff --quiet HEAD  # dirty check (non-zero = dirty)
git -C <repo_path> checkout -b <branch>
git -C <repo_path> add -A
git -C <repo_path> commit -m "<message>"
git -C <repo_path> push origin <branch>
```

---

## Decision 5: Commit message format

**Decision**: `feat: <spec-name> [bureau/<run-id-prefix>]`

**Example**: `feat: smoke-hello-world [bureau/deaaf184]`

**Rationale**: Conventional commit format (`feat:`). Square bracket suffix provides traceability back to the bureau run without polluting the commit subject. Matches the branch naming convention.

---

## Decision 6: Collision handling

**Decision**: Append `-2`, `-3` up to 3 total attempts. If all three names exist remotely, escalate with `GIT_BRANCH_EXISTS`.

**Rationale**: Three attempts covers the common case (previous aborted runs from the same spec). More than 3 suggests a systemic issue that warrants human intervention.

---

## Decision 7: State propagation

**Decision**: `git_commit_node` writes `branch_name` to state. `pr_create_node` reads `branch_name` from state (already present as a field on `Spec`; this formalises it). The PR create node uses the pushed branch name — no change to its `gh pr create` call needed since `gh` reads the current branch from the repo.

**Note**: `gh pr create` is run with `cwd=repo_path` and no `--head` flag — it uses the current branch of the repo, which `git_commit_node` will have set.
