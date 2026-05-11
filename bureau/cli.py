from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from bureau import events
from bureau.config import load_bureau_config
from bureau.graph import build_graph
from bureau.run_manager import (
    RunNotFoundError,
    RunNotPausedError,
    abort_run,
    create_run,
    get_run,
    init_repo,
    list_runs,
    prune_runs,
    resume_run,
    write_run_record,
    write_run_summary,
)
from bureau.state import Phase, RunStatus, make_initial_state

load_dotenv(Path.home() / ".bureau" / ".env", override=False)

app = typer.Typer(name="bureau", help="Autonomous ASDLC runtime — spec file in, pull request out.")

_PERSONA_COMMANDS = {"run", "resume"}


@app.callback(invoke_without_command=True)
def _check_api_key(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand in _PERSONA_COMMANDS and not os.environ.get("ANTHROPIC_API_KEY"):
        typer.echo(
            "[bureau] error: ANTHROPIC_API_KEY not set"
            " — add it to ~/.bureau/.env or export it in your shell",
            err=True,
        )
        raise typer.Exit(1)


@app.command()
def run(
    spec: str = typer.Argument(..., help="Path to spec folder or spec.md file"),
    repo: str = typer.Option(".", help="Path to target repository"),
    config: Optional[str] = typer.Option(None, help="Path to bureau.toml"),
) -> None:
    """Execute the ASDLC workflow from a spec folder or spec file."""
    spec_arg = Path(spec).resolve()
    if spec_arg.is_dir():
        spec_folder = spec_arg
        spec_path = spec_folder / "spec.md"
        tasks_path = spec_folder / "tasks.md"
    else:
        spec_path = spec_arg
        spec_folder = spec_path.parent
        tasks_path = spec_folder / "tasks.md"

    repo_path = str(Path(repo).resolve())

    if not spec_path.exists():
        typer.echo(f"Error: spec file not found: {spec_path}", err=True)
        raise typer.Exit(1)

    bureau_config = load_bureau_config(config)
    record = create_run(str(spec_path), repo_path)
    run_id = record.run_id

    events.emit(events.RUN_STARTED, id=run_id, spec=spec, repo=repo)

    compiled = build_graph(run_id, bureau_config)
    initial_state = make_initial_state(
        run_id,
        str(spec_path),
        repo_path,
        spec_folder=str(spec_folder),
        tasks_path=str(tasks_path),
    )
    thread_config = {"configurable": {"thread_id": run_id}}

    start = time.monotonic()
    try:
        for _ in compiled.stream(initial_state, config=thread_config):
            pass
    except Exception as exc:
        record = get_run(run_id)
        record.status = RunStatus.FAILED
        record.current_phase = Phase.FAILED
        write_run_record(record)
        write_run_summary({"run_id": run_id, "spec_path": record.spec_path}, "failed")
        events.emit(events.RUN_FAILED, id=run_id, phase=record.current_phase, error=str(exc))
        raise typer.Exit(2)

    duration = time.monotonic() - start
    record = get_run(run_id)

    if record.status == RunStatus.PAUSED:
        return

    record.status = RunStatus.COMPLETE
    record.current_phase = Phase.COMPLETE
    write_run_record(record)
    events.emit(events.RUN_COMPLETED, id=run_id, duration=f"{duration:.1f}s")


@app.command()
def resume(
    run_id: str = typer.Argument(..., help="Run ID to resume"),
    response: str = typer.Option("", help="Response to escalation question"),
) -> None:
    """Resume a paused run from its last checkpoint."""
    try:
        record = resume_run(run_id, response)
    except RunNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except RunNotPausedError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    bureau_config = load_bureau_config(None)
    compiled = build_graph(run_id, bureau_config)
    thread_config = {"configurable": {"thread_id": run_id}}

    start = time.monotonic()
    events.emit(events.RUN_STARTED, id=run_id, spec=record.spec_path, repo=record.repo_path)

    try:
        for _ in compiled.stream(None, config=thread_config):
            pass
    except Exception as exc:
        record = get_run(run_id)
        record.status = RunStatus.FAILED
        write_run_record(record)
        write_run_summary({"run_id": run_id, "spec_path": record.spec_path}, "failed")
        events.emit(events.RUN_FAILED, id=run_id, phase=record.current_phase, error=str(exc))
        raise typer.Exit(2)

    duration = time.monotonic() - start
    record = get_run(run_id)
    if record.status != RunStatus.PAUSED:
        record.status = RunStatus.COMPLETE
        record.current_phase = Phase.COMPLETE
        write_run_record(record)
        events.emit(events.RUN_COMPLETED, id=run_id, duration=f"{duration:.1f}s")


@app.command(name="list")
def list_cmd(
    status: Optional[str] = typer.Option(None, help="Filter by status"),
) -> None:
    """List all runs."""
    runs = list_runs(status)
    if not runs:
        typer.echo("No runs found.")
        return
    for r in runs:
        typer.echo(f"{r.run_id}\t{r.status}\t{r.started_at}\t{r.spec_path}")


@app.command()
def show(run_id: str = typer.Argument(..., help="Run ID to show")) -> None:
    """Show details of a run."""
    try:
        record = get_run(run_id)
    except RunNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    for key, value in record.__dict__.items():
        typer.echo(f"{key}: {value}")


@app.command()
def abort(run_id: str = typer.Argument(..., help="Run ID to abort")) -> None:
    """Abort a run."""
    try:
        abort_run(run_id)
        typer.echo(f"Run {run_id} aborted.")
    except RunNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


@app.command()
def prune(
    dry_run: bool = typer.Option(True, help="Print candidates without deleting (default: on)"),
    older_than: Optional[int] = typer.Option(None, help="Delete runs last updated more than N days ago"),
    status: Optional[str] = typer.Option(None, help="Restrict to runs with this status"),
    missing_spec: bool = typer.Option(False, help="Delete runs whose spec file no longer exists"),
) -> None:
    """Remove old run directories from ~/.bureau/runs/."""
    if older_than is None and not missing_spec:
        typer.echo("No filter specified — pass --older-than N and/or --missing-spec.", err=True)
        raise typer.Exit(1)

    results = prune_runs(
        dry_run=dry_run,
        older_than_days=older_than,
        status_filter=status,
        missing_spec=missing_spec,
    )

    if not results:
        typer.echo("No runs matched the given criteria.")
        return

    label = "[dry-run] would delete" if dry_run else "deleted"
    for r in results:
        typer.echo(f"{label}  {r.run_id}  ({r.reason})")

    typer.echo(f"\n{len(results)} run(s) {'would be ' if dry_run else ''}removed.")
    if dry_run:
        typer.echo("Re-run with --no-dry-run to delete.")


@app.command(name="init")
def init_cmd(
    repo: str = typer.Option(".", help="Target repository path"),
) -> None:
    """Scaffold .bureau/config.toml in a target repository."""
    result = init_repo(repo)
    config_path = Path(repo) / ".bureau" / "config.toml"
    if result == "exists":
        typer.echo(f"Warning: {config_path} already exists. Not overwriting.")
    else:
        typer.echo(f"Created {config_path}")
        typer.echo("Edit it to fill in FILL_IN placeholders before running bureau.")
