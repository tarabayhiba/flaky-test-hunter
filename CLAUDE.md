# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

flake-hunter runs a target pytest suite N times, diffs per-test outcomes
across runs, and flags tests whose fail-rate falls strictly between two
configurable thresholds (0% and 100% are "consistently passing/failing",
not flaky). Findings can be written to a persistent Markdown ledger
and/or applied as skip/xfail marks in the target repo.

## Commands

All commands assume the local ROS2 `PYTHONPATH` leak (see "Local
environment gotcha" below) — prefix with `env -u PYTHONPATH` any time you
hit a spurious `ModuleNotFoundError: lark`.

```bash
# Lint / format / type-check
env -u PYTHONPATH ruff check .
env -u PYTHONPATH ruff format .
env -u PYTHONPATH mypy .

# Full local gate (ruff + mypy, pinned to versions in .venv) — also runs
# automatically before every `git commit` via a PreToolUse hook
env -u PYTHONPATH .venv/bin/pre-commit run --all-files

# Run this repo's own unit suite (tests/unit/ only — see testpaths)
env -u PYTHONPATH pytest

# Run a single test
env -u PYTHONPATH pytest tests/unit/test_aggregator.py::test_name -v

# Run flake-hunter against its own ground-truth fixture (once cli.py is
# wired — currently raises NotImplementedError, see below)
env -u PYTHONPATH flake-hunter --config flake_hunter.toml
```

Do not chase the `ModuleNotFoundError: lark` failure as a project bug —
it comes from a sourced ROS2 `setup.bash` polluting every venv's
`PYTHONPATH` on this machine, and breaks pytest's plugin autoload.

## Architecture

Pipeline, in data-flow order (see each module's docstring for the
authoritative contract):

```
config.load_config()
  -> runner.run_suite_n_times()   # N pytest subprocesses -> RunManifest (paths only)
  -> parser.parse_run()           # one JSON report -> dict[nodeid, TestOutcome]
  -> aggregator.aggregate()       # per-run outcomes -> list[FlakeReport]
  -> report.render_markdown()     # FlakeReport list -> Markdown
  -> quarantine.write_known_flakes() / apply_quarantine_marks()
```

`cli.py` is meant to wire this whole chain into one runnable command.

**Implementation status** (don't assume a module is done just because
its signature exists — check for `raise NotImplementedError`):
- Implemented: `runner.py`, `parser.py`, `aggregator.py` (Phase 2).
- Stubs, not yet implemented: `config.py`, `report.py`, `quarantine.py`,
  `cli.py` (Phase 3 — see `plan.md` for the phase breakdown and the
  design decisions behind each module, including things explicitly
  deferred like multi-repo support and dry-run quarantine).

Key design points worth knowing before touching this code:
- `runner.py` never returns log/report contents directly, only paths on
  a `RunManifest` — callers read artifacts from disk lazily. A crashed
  subprocess or a run that times out is recorded as a failed
  `RunRecord`, not raised, so one bad run can't take down the batch.
- `parser.py` degrades a missing/truncated/malformed JSON report to `{}`
  rather than raising, for the same reason.
- `aggregator.aggregate()`'s flakiness rule is **strict** inequality on
  both bounds (`min_fail_rate < fail_rate < max_fail_rate`) — this is
  intentional domain logic, not a boundary bug.
- `tests/fixtures/flaky_demo_suite/` is the ground-truth fixture: three
  deliberately flaky tests (random, shared-temp-file race, timing
  deadline) plus two stable controls. It's excluded from this repo's own
  `testpaths` (flake-hunter runs *against* it, doesn't collect it as its
  own tests) and is asserted against end-to-end in
  `tests/unit/test_pipeline_against_fixture.py`.

## Commit discipline

- **Never run `git commit` without asking first, every time.** Show what's
  staged and the proposed message, then wait for explicit approval. This
  applies even mid-task, even for small or "obviously fine" commits, even
  if an earlier commit in the same session was already approved — approval
  does not carry over to the next commit.
- Commit granularity: one commit per working, revertible unit, not one per
  build phase. Some phases produce several commits; that's expected.
- Never `--amend`, force-push, or rewrite history that's already been
  pushed without asking separately for that too.
- Commit subjects use a Conventional Commits prefix: `feat:`, `fix:`,
  `test:`, `docs:`, `chore:`, `refactor:`, `ci:`, `build:`. Pick the one
  that matches what actually changed (e.g. stub scaffolding with no
  behavior is `chore:`, not `feat:`; a pytest fixture suite is `test:`;
  CLAUDE.md/ARCHITECTURE.md-only changes are `docs:`).

## Branching

- The Phase 0 scaffold lives directly on `main`.
- From there on, work happens on a branch per phase (or per meaningful
  chunk of work within a phase, if a phase is large) — not directly on
  `main`. Cut the branch before starting the phase's work, not after.
- Plain branch switching (`git checkout -b`), not `git worktree` —
  considered and decided against: this is solo, sequential work (one
  phase at a time, not parallel streams), so a second working directory
  doesn't solve a real friction point here.
- Delete each branch after it's merged into `main` (`git branch -d`,
  which only succeeds if fully merged — safe by construction). The
  commits live on in `main`'s history either way; no reason to keep the
  branch pointer around.

## Project shape

- Flat package layout: `flake_hunter/` (no `src/` — not publishing this).
- Module contracts (see each module's docstring for the authoritative
  signature):
  - `runner.py` — spawns pytest N times, writes JSON reports + raw console
    logs to disk, returns a `RunManifest` of paths only. Never returns log
    contents directly.
  - `parser.py` — parses one `pytest --json-report` file into
    `dict[str, TestOutcome]`.
  - `aggregator.py` — turns a `RunManifest` into `list[FlakeReport]`. A
    test is flaky iff its fail-rate is strictly between `min_fail_rate`
    and `max_fail_rate` — 0% and 100% are not flaky.
  - `quarantine.py` — dual-mode: `write_known_flakes` merges into
    `memory/known_flakes.md` (append/merge only, never overwrite history);
    `apply_quarantine_marks` writes conftest/marker config into the target
    repo. Selected via `mode = "report" | "apply" | "both"`.
  - `report.py` — renders `list[FlakeReport]` to Markdown for CLI/CI/PR use.
  - `config.py` — loads/validates `flake_hunter.toml` (this tool's
    user-facing run config — distinct from `pyproject.toml`, which is
    packaging/tooling config for this repo).
- `memory/known_flakes.md` — persistent domain ledger (test id, first
  seen, pass/fail counts, suspected cause, status). Not agent memory —
  don't confuse with this file.
- `metrics/runs/` — one timestamped JSON per flake-hunter invocation
  (duration, tests analyzed, flakes found), committed to show trend
  over time.
- `.flake_hunter/` (gitignored) — ephemeral raw per-run JSON reports and
  console logs from `runner.py`. Large and disposable; never committed.
- `tests/fixtures/flaky_demo_suite/` — small pytest suite with
  deliberately flaky tests (random-based, shared-temp-file race,
  timing-dependent). Ground truth for testing every module and the
  reliable thing to demo against live. Not part of the real unit-test run
  (`pytest.ini_options.testpaths` excludes it) — flake-hunter is meant to
  run *against* it, not collect it as part of its own suite.

## Tooling

- `ruff check .` / `ruff format` — lint + format, strict-ish select
  (`E W F I UP B SIM C4 N RUF`). Fix real issues, don't suppress
  (e.g. use `StrEnum`, not `class X(str, Enum)`).
- `mypy` — strict mode. All code must be fully typed.
- `pre-commit run --all-files` before considering work done; hooks are
  pinned to the versions actually installed in `.venv`.
- Local environment gotcha: this machine has a global ROS2 `PYTHONPATH`
  (from a sourced `setup.bash`) that leaks into every venv and breaks
  pytest's plugin autoload (`launch_testing` fails on a missing `lark`
  import). Run pytest/mypy here with `env -u PYTHONPATH <cmd>` if you hit
  an unrelated `ModuleNotFoundError: lark` — it's not a project bug.

## Workflow

- Typed code, lint-clean, tested — before every commit, not just at the
  end.
- Don't relitigate the architecture decisions already made for this
  project (module contracts above); implement against them.
- `plan.md` is the forward-looking roadmap and the design-decision record
  (phase status, what's explicitly deferred and why). Check it before
  assuming something is unbuilt-by-oversight rather than unbuilt-by-choice.
