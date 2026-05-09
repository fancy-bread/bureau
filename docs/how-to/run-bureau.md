---
icon: octicons/play-24
---

# Run Bureau

## bureau run

```sh
bureau run <spec> --repo <path>
```

`<spec>` can be a path to `spec.md` or the spec folder — bureau resolves `spec.md` and `tasks.md` from either. `--repo` defaults to `.`, so running from inside the target repo is the normal workflow.

```sh
# From inside the target repo
bureau run ../my-project-specs/001-feature/spec.md

# From anywhere, explicit repo
bureau run specs/001-feature --repo /path/to/repo

# Custom bureau.toml
bureau run specs/001-feature --config /path/to/bureau.toml
```

Bureau requires `ANTHROPIC_API_KEY` before starting. If it is not set, the run exits immediately with an error.

---

## bureau resume

Continues a paused run from its last checkpoint. No phases before the pause point are re-run.

```sh
bureau resume <run-id>

# With a response to the escalation
bureau resume <run-id> --response "AuthService.refreshToken() takes (token: str) -> str"
```

---

## Run management

```sh
bureau list                          # all runs
bureau list --status paused          # filter: running, paused, complete, failed
bureau show <run-id>                 # full run record
bureau abort <run-id>                # cancel a run
```

### Pruning old runs

```sh
bureau prune --older-than 7                        # dry-run: show runs older than 7 days
bureau prune --older-than 7 --no-dry-run           # delete them
bureau prune --missing-spec --no-dry-run           # delete runs whose spec no longer exists
```

`--dry-run` is on by default. Always preview before deleting.

---

## Output formats

Controlled by `BUREAU_OUTPUT_FORMAT` in `~/.bureau/.env` or shell environment.

=== "Text (default)"

    ```
    [bureau] run.started          id=run-a3f9c2b1  spec=specs/001-feature/spec.md
    [bureau] phase.started        phase=validate_spec
    [bureau] phase.completed      phase=validate_spec  duration=0.3s
    [bureau] builder.tool         tool=write_file  path=src/feature.py
    [bureau] builder.tool         tool=run_command  exit_code=0
    [bureau] reviewer.pipeline    passed=true
    [bureau] reviewer.verdict     verdict=pass  findings=1
    [bureau] pr.created           id=run-a3f9c2b1  pr=https://github.com/org/repo/pull/42
    [bureau] run.completed        id=run-a3f9c2b1  duration=6m01s
    ```

=== "CloudEvents NDJSON"

    ```sh
    BUREAU_OUTPUT_FORMAT=cloudevents bureau run specs/001-feature
    ```

    ```json
    {"specversion":"1.0","id":"8b67eaba...","source":"urn:bureau:run:run-a3f9c2b1","type":"com.fancybread.bureau.run.started","time":"2026-05-08T14:32:00Z","datacontenttype":"application/json","data":{"id":"run-a3f9c2b1","spec":"specs/001-feature/spec.md"}}
    ```

    One JSON object per line. See [Events](../reference/events.md) for the full catalog.
