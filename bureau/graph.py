from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from bureau.config import BureauConfig
from bureau.nodes.builder import builder_node
from bureau.nodes.critic import critic_node
from bureau.nodes.escalate import escalate_node
from bureau.nodes.git_commit import git_commit_node
from bureau.nodes.memory_node import memory_node
from bureau.nodes.pr_create import pr_create_node
from bureau.nodes.repo_analysis import repo_analysis_node
from bureau.nodes.tasks_loader import tasks_loader_node
from bureau.nodes.validate_spec import validate_spec_node


def _route_validate(state: dict[str, Any]) -> str:
    return state.get("_route", "ok")


def _route_tasks_loader(state: dict[str, Any]) -> str:
    return state.get("_route", "ok")


def _route_critic(state: dict[str, Any]) -> str:
    return state.get("_route", "pass")  # critic_node sets _route: pass | revise | escalate


def _route_git_commit(state: dict[str, Any]) -> str:
    return state.get("_route", "ok")


def build_graph(run_id: str, config: BureauConfig | None = None) -> Any:
    checkpoint_path = Path.home() / ".bureau" / "runs" / run_id / "checkpoint.db"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    graph = StateGraph(dict)

    graph.add_node("validate_spec", validate_spec_node)
    graph.add_node("repo_analysis", repo_analysis_node)
    graph.add_node("memory", memory_node)
    graph.add_node("tasks_loader", tasks_loader_node)
    graph.add_node("builder", builder_node)
    graph.add_node("critic", critic_node)
    graph.add_node("git_commit", git_commit_node)
    graph.add_node("pr_create", pr_create_node)
    graph.add_node("escalate", escalate_node)

    graph.set_entry_point("validate_spec")

    graph.add_conditional_edges(
        "validate_spec",
        _route_validate,
        {"ok": "repo_analysis", "escalate": "escalate"},
    )
    graph.add_conditional_edges(
        "repo_analysis",
        _route_validate,
        {"ok": "memory", "escalate": "escalate"},
    )
    graph.add_edge("memory", "tasks_loader")
    graph.add_conditional_edges(
        "tasks_loader",
        _route_tasks_loader,
        {"ok": "builder", "escalate": "escalate"},
    )
    graph.add_edge("builder", "critic")
    graph.add_conditional_edges(
        "critic",
        _route_critic,
        {"pass": "git_commit", "revise": "builder", "escalate": "escalate"},
    )
    graph.add_conditional_edges(
        "git_commit",
        _route_git_commit,
        {"ok": "pr_create", "escalate": "escalate"},
    )
    graph.add_edge("pr_create", END)
    graph.add_edge("escalate", END)

    conn = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return graph.compile(checkpointer=checkpointer)
