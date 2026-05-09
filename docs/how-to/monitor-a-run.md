---
icon: octicons/pulse-24
---

# Monitor a Run

---

## Text output

The default. Every bureau event is printed to stdout as a structured key=value line:

```
[bureau] run.started          id=run-a3f9c2b1  spec=specs/001-feature/spec.md
[bureau] phase.started        phase=builder
[bureau] ralph.started        round=1
[bureau] ralph.attempt        round=1  attempt=1
[bureau] builder.tool         tool=write_file  path=src/feature.py
[bureau] builder.tool         tool=run_command  exit_code=0
[bureau] ralph.completed      round=1  passed=true
[bureau] reviewer.pipeline    passed=true
[bureau] reviewer.verdict     verdict=pass  findings=1
[bureau] phase.completed      phase=reviewer  duration=42.1s
[bureau] pr.created           id=run-a3f9c2b1  pr=https://github.com/org/repo/pull/42
[bureau] run.completed        id=run-a3f9c2b1  duration=364.2s
```

To capture output for later inspection:

```sh
bureau run specs/001-feature 2>&1 | tee run-$(date +%s).txt
```

---

## CloudEvents NDJSON

Set `BUREAU_OUTPUT_FORMAT=cloudevents` to emit [CloudEvents 1.0](https://cloudevents.io) NDJSON — one JSON object per line, parseable by any structured log consumer.

```sh
BUREAU_OUTPUT_FORMAT=cloudevents bureau run specs/001-feature
```

Each line is a spec-compliant CloudEvent envelope:

```json
{
  "specversion": "1.0",
  "id": "8b67eaba-...",
  "source": "urn:bureau:run:run-a3f9c2b1",
  "type": "com.fancybread.bureau.reviewer.verdict",
  "time": "2026-05-08T14:32:00Z",
  "datacontenttype": "application/json",
  "data": { "verdict": "pass", "findings": 1 }
}
```

See [Events](../reference/events.md) for the full event type catalog.

---

## Kafka

When `BUREAU_KAFKA_BOOTSTRAP_SERVERS` is set, every CloudEvent is also published to a Kafka topic — independently of `BUREAU_OUTPUT_FORMAT`. Stdout format is unaffected.

```sh
# ~/.bureau/.env
BUREAU_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
BUREAU_KAFKA_TOPIC=bureau.runs          # default
BUREAU_INSTANCE_ID=worker-1             # optional stable identity
```

Start a local Redpanda instance for development:

```sh
make bureau-kafka-up    # start
make bureau-kafka-down  # stop
```

Publishing is best-effort (`acks=1`, `retries=0`). Broker failures are logged to stderr and never affect the run outcome.

---

## Run summary

At every run terminus (pass, escalated, or failed), bureau writes a structured summary to `~/.bureau/runs/<run-id>/run-summary.json`:

```json
{
  "run_id": "run-a3f9c2b1",
  "spec_path": "specs/001-feature/spec.md",
  "verdict": "pass",
  "pr_url": "https://github.com/org/repo/pull/42",
  "duration_seconds": 364,
  "ralph_rounds": 1,
  "timestamp": "2026-05-08T14:38:00Z"
}
```

This file is also attached as a CI artifact when bureau runs in GitHub Actions — useful for post-run inspection without needing to stream stdout.

