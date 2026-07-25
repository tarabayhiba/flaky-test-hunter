# flake-hunter — agent conventions

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
