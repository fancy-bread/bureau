---
icon: octicons/terminal-24
---

# CLI

## bureau run

Execute a spec against a target repo.

```sh
bureau run <spec> [OPTIONS]
```

| Argument / Option | Default | Description |
|---|---|---|
| `spec` | required | Path to `spec.md` or the spec folder |
| `--repo` | `.` | Path to the target repository |
| `--config` | `bureau.toml` | Path to `bureau.toml` |

**Exit codes:** `0` = completed, `1` = startup error (missing key, bad args), `2` = run failed mid-execution.

---

## bureau resume

Continue a paused run from its last checkpoint.

```sh
bureau resume <run-id> [OPTIONS]
```

| Argument / Option | Default | Description |
|---|---|---|
| `run-id` | required | Run ID from `bureau list` |
| `--response` | `""` | Context to inject for the escalation |

---

## bureau list

List runs, optionally filtered by status.

```sh
bureau list [OPTIONS]
```

| Option | Description |
|---|---|
| `--status` | Filter by status: `running`, `paused`, `complete`, `failed` |

---

## bureau show

Show the full record for a run.

```sh
bureau show <run-id>
```

---

## bureau abort

Cancel a running or paused run.

```sh
bureau abort <run-id>
```

---

## bureau prune

Remove old run directories from `~/.bureau/runs/`. Dry-run by default.

```sh
bureau prune [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--older-than` | — | Delete runs last updated more than N days ago |
| `--status` | — | Restrict to runs with this status |
| `--missing-spec` | `false` | Delete runs whose spec file no longer exists |
| `--dry-run / --no-dry-run` | `true` | Preview without deleting |

At least one of `--older-than` or `--missing-spec` must be provided.

---

## bureau init

Scaffold `.bureau/config.toml` in a target repository.

```sh
bureau init [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--repo` | `.` | Target repository path |

Does not overwrite an existing `config.toml`.
