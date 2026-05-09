---
icon: octicons/law-24
---

# Constitution

Bureau governs agent behaviour through layered constitutions. The [Agent Constitution pattern](https://asdlc.io/patterns/agent-constitution) from ASDLC describes the principle: persistent, high-level directives that shape what an agent will and won't do, loaded before any action begins.

Bureau applies this in three layers, each injected into the Builder and Reviewer at run time.

---

## Layer 1 — Bureau Runtime Constitution

**Source:** `bureau/data/constitution.md` (bundled in the bureau package)

The non-negotiable runtime rules. Always injected, cannot be overridden by any project. Defines the six principles that govern every run:

| Principle | Short form |
|---|---|
| I. Spec-First Execution | No implementation without an approved spec |
| II. Escalate, Don't Guess | Surface uncertainty; never hallucinate an answer |
| III. Verification Gates Are Real Gates | Tests must pass; "probably works" is not a bureau state |
| IV. Constitution-First Compliance | Constitution violations are CRITICAL and block PR creation |
| V. Terse, Structured Output | Events only; no conversational filler |
| VI. Autonomous Operation With Resumability | No mid-run check-ins; every node checkpointed |

It also defines the Builder's phase-end commit obligation: after each spec phase passes its verification gate, the Builder MUST commit with a message identifying the phase. One commit per completed phase, not one commit per run.

Constitution violations found by the Reviewer are CRITICAL findings. No PR is created until they are resolved.

---

## Layer 2 — Spec Kit Constitution

**Source:** `.specify/memory/constitution.md` in the target repo

The project-level architectural constitution, produced when the developer runs `specify init` and maintained as the project evolves. Contains the principles that govern *this* project specifically — naming conventions, architectural patterns, security rules, performance constraints.

Bureau appends this to the runtime constitution when it exists. The Builder and Reviewer both see it. This is how a project's established standards travel into every bureau run automatically, without the developer having to repeat them in every spec.

If the target repo has no `.specify/memory/constitution.md`, only the runtime constitution is used.

---

## Layer 3 — AGENTS.md / CLAUDE.md

**Source:** `AGENTS.md` and/or `CLAUDE.md` in the target repo

Project-level agent directives read directly by Claude Code and deepagents. While not injected by bureau explicitly, they are part of the context that the Builder agent operates within — deepagents respects `AGENTS.md` as part of its standard context loading.

These files are best suited for conventions that apply to any AI working in the repo: file structure, coding style, what not to touch. The Spec Kit constitution is the right home for architectural principles that bureau's Reviewer should enforce; `AGENTS.md` / `CLAUDE.md` are the right home for developer-facing conventions.

---

## Precedence

When principles conflict across layers, the runtime constitution wins. A project constitution cannot override Principle IV (constitution-first compliance) or Principle II (escalate, don't guess). It can add constraints; it cannot remove them.

```
Bureau runtime constitution   ← always applies, cannot be overridden
    +
Spec Kit constitution         ← appended per-repo
    +
AGENTS.md / CLAUDE.md         ← ambient agent context
```
