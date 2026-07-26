# Fast-iteration-loop demo — plan

Status: ready-for-implementation
Last updated: 2026-07-26

## Overview

A ~5-minute lightning demo (2026-07-27) of the Claude Code setup built
around this repo. The subject isn't flake-hunter's test-flakiness logic —
it's the *development loop* around this repo (CLAUDE.md memory, custom
skills, subagents, MCP tool connections), and the claim that it has been
deliberately engineered to optimize for fast iteration, minimal
redundancy, and reduced friction while coding. The demo exists to show
that claim holds up end-to-end, live, not just on paper.

## Goals & Non-Goals

**Goals**
- Present CLAUDE.md as the project's persistent memory.
- Demonstrate two custom skills: `guided-plan` (meta — this very doc was
  produced by it) and `doc-sync`.
- Demonstrate the two project subagents: `py-expert` and `qa-engineer`,
  via a real (not staged) piece of work.
- Demonstrate the Context7 MCP tool connection with a live docs lookup.
- Run the actual tool end-to-end and show real output.
- Close by explicitly naming the goal and asserting it was met.

**Non-Goals**
- Not implementing the "non-flaking status" ledger feature in this
  session — the user is doing that themselves before the demo.
- Not redesigning any `flake_hunter` module contract.
- Not a walkthrough of flake-hunter's domain logic (fail-rate math,
  quarantine modes) beyond what's needed to narrate the live run.

## Scope

In bounds: a runbook script + timing budget, a recap artifact, and a
one-time rehearsal run of the real pipeline to de-risk the live demo.
Out of bounds: any code change to `flake_hunter/`.

## Requirements

### Functional
- Runbook must name exact commands, not paraphrases, so nothing is
  improvised live.
- Runbook must fit a 5-minute budget with an explicit cut list for
  running long.

### Non-functional
- Reliability: the live run must be pre-verified today (rehearsal), since
  a failure live in front of an audience is the one unrecoverable risk.
- No committed side effects from rehearsal without explicit approval.

## Approach

### Deliverable format
- Options considered: runbook-only, slide-only, checklist-only, runbook +
  artifact recap.
- Chosen: **runbook + artifact recap** — the runbook is what's read from
  live; the artifact is a shareable leave-behind afterward.

### Time budget
- Options considered: ~5 min lightning, ~10 min technical, ~20-30 min
  walkthrough.
- Chosen: **~5 min lightning** — forces a strict per-section timebox and
  an explicit cut list (see runbook).

### Subagent demo liveness
- Options considered: live real task in front of the audience, pre-staged
  replay, config-only walkthrough.
- Chosen: **real task, done ahead of time by the user** (not live in the
  5-minute window, and not dispatched by Claude in this planning
  session). The concrete task: add a "non-flaking" status to
  `memory/known_flakes.md` — `flake_hunter/quarantine.py`'s
  `write_known_flakes` currently always stamps `status="flaky"` and never
  marks a previously-flaky test as resolved once it stabilizes. The
  runbook references the resulting commit rather than re-running the
  subagents live, since a live implementation + review pass doesn't fit
  a 5-minute total budget alongside everything else.

### Rehearsal
- Chosen: run the real pipeline now (this session) to catch problems
  before presenting live, rather than trusting it untested.

## Scalability & best-practice notes

This plan is scoped entirely to a one-time demo; nothing here is meant to
generalize beyond it. The runbook's cut list is the explicit signal for
"what's safe to drop under time pressure" so that decision isn't made
live, under pressure, for the first time.

## Open Questions

None blocking. See the runbook's note on section 2:15–3:15 for how it
adapts if the user's own ledger-status implementation isn't merged by
demo time.

## Decision Log

- 2026-07-26: Subagent demo task locked to "add non-flaking status to
  known_flakes.md" and left for the user to implement themselves —
  confirmed by reading `quarantine.py`'s `write_known_flakes`, which
  never transitions a resolved test out of `status="flaky"`.
- 2026-07-26: Time budget set to ~5 min lightning — drives every other
  sizing decision in the runbook.
- 2026-07-26: Deliverable set to runbook (docs/plans/) + HTML artifact
  recap.
- 2026-07-26: Rehearsed the real end-to-end command
  (`env -u PYTHONPATH .venv/bin/flake-hunter --config flake_hunter.toml`)
  — completed in ~2.3s, correctly flagged the 3 known-flaky fixture
  tests, no failures.
