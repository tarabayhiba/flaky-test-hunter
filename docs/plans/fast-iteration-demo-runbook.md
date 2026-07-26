# Fast-iteration-loop demo — runbook


## 0:00–0:30 — Thesis (say this first, verbatim-ish)

> "The goal was to optimize that loop for fast iteration, minimal
> redundancy, and reduced friction. Everything I show you in the next
> five minutes is proof of that, running live."

## 0:30–1:15 — CLAUDE.md (the memory file)

Open `CLAUDE.md`. Point at, in order:
- **Architecture** section — the pipeline stages
  (`config → runner → parser → aggregator → report → quarantine`).
- **Workflow** — "Don't relitigate the architecture decisions already
  made for this project."
- **Commit discipline** — never commits without asking, every time.

One line: *"This is why Claude doesn't re-derive the same architecture,
or re-ask the same settled questions, every single session."*

## 1:15–2:15 — Skills: guided-plan + doc-sync

- Point at `docs/plans/fast-iteration-demo.md` and
  `docs/plans/fast-iteration-demo-runbook.md` — *this demo itself* was
  planned by running `/guided-plan` and answering a handful of
  multiple-choice questions instead of Claude just deciding the format,
  timing, and scope unilaterally.
- Mention `/doc-sync`: keeps `README.md`/`ARCHITECTURE.md` matched to the
  actual code on demand, rather than docs quietly rotting. Run it live
  only if time allows (see cut list); otherwise just name it.

## 2:15–3:15 — Subagents: py-expert + qa-engineer

- new branch

*
## 3:15–4:00 — Context7 MCP

Live query: look up `pytest-json-report`'s report schema/config options —
this is the exact format `flake_hunter/parser.py` consumes. One line:
*"This pulls current docs live, instead of guessing from training data
that might be stale."*

## 4:00–4:45 — End-to-end run

```bash
env -u PYTHONPATH .venv/bin/flake-hunter --config flake_hunter.toml
```

Real output: a Markdown flakiness table for the 3 known-flaky fixture
tests. Then open `memory/known_flakes.md` and point at the row(s) —
including the status column, showing `flaky` vs. `resolved`/non-flaking
if that landed.

## 4:45–5:00 — Close

> "That's the whole loop: a memory file so context isn't rebuilt every
> session, skills so planning and docs aren't done from scratch each
> time, subagents with scoped, non-overlapping jobs, a live tool
> connection for current docs, and a real pipeline that actually runs.
> Fast iteration, minimal redundancy, reduced friction — that was the
> goal, and this is it working."

---

## Cut list (drop in this order if running long)

1. Context7 section → shrink to naming it, skip the live query.
2. Subagent section → skip opening the agent config files, just show the
   commit (or skip entirely if not merged).
3. Skills section → mention doc-sync exists, don't run it live.

Never cut: the thesis open, the end-to-end run, or the close — those
three are the actual proof.
