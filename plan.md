# flake-hunter — implementation plan

Forward-looking roadmap + the design decisions behind it. Distinct from
`ARCHITECTURE.md` (see Phase 3), which documents the system as actually
built, after the fact — this is the plan going in.

## Status

- Phase 0 (scaffold) — done, merged to `main`.
- Phase 1 (demo fixture) — done, merged to `main`.
- Phase 2 (core pipeline) — next.
- Phase 3 (output modes + orchestration) — not started.
- `.claude/agents/log-analyzer.md` and
  `.claude/skills/investigate-flaky-test/SKILL.md` — not built (the
  skill's directory exists but is empty), and no longer tracked in this
  roadmap now that Phases 4-5 have been dropped (see "Explicitly
  deferred").
- Harness tooling built ahead of phase order, independent of the
  roadmap above:
  - `.claude/agents/py-expert.md` — Python implementation subagent for
    `flake_hunter/`/`tests/` work.
  - `.claude/agents/qa-engineer.md` — adversarial QA subagent that
    reviews uncommitted `flake_hunter/`/`tests/` changes (git diff/status
    against HEAD) before commit, trying to break them; doesn't fix bugs
    or plan architecture itself.
  - A Claude Code `PreToolUse` hook (`.claude/settings.json`) runs
    `pre-commit` (ruff + mypy) before every `git commit`, replacing the
    git-native pre-commit hook.
  - `.mcp.json` exists with the Context7 MCP server (library docs
    lookup).
  - The global `guided-plan` skill (options-driven planning, not
    project-specific) is available for producing planning docs like
    this one.

## Key design decisions

Beyond the original module contracts (see `CLAUDE.md`), these were
resolved through discussion and aren't in the original brief:

- **Orchestration (`cli.py`)**: not owned by Phase 2 or Phase 3
  individually — wiring its real body (`config.load_config()` →
  `runner.run_suite_n_times()` → `parser.parse_run()` →
  `aggregator.aggregate()` → `report.render_markdown()` /
  `quarantine.write_known_flakes()`) is the closing step of Phase 3,
  once every module it depends on is real.
- **`runner.py`'s `parallel` parameter**: concurrent pytest subprocess
  invocations via a thread pool (`ThreadPoolExecutor(max_workers=parallel)`),
  each running the full suite as its own OS process. This was previously
  undefined and caused a near-miss bug in the Phase 1 fixture (a shared
  temp-file path that would've raced across concurrent invocations, not
  just within one) before being pinned down.
- **Scope: this repo first, expandable to other local repos later.**
  flake-hunter's primary target for this project is analyzing itself,
  but the design should stay expandable to other repos down the line —
  always assuming the target is already checked out **locally** with its
  dependencies already installed (see "Environment for running tests"
  below). No cloning, no dependency provisioning, ever — that's out of
  scope by definition, not just deferred. `target_repo_path` and
  `suite_path` stay real parameters (not hardcoded to `.`), so pointing
  flake-hunter at a different local repo already works structurally.
  What's still not built: the safety machinery real multi-repo use would
  need — dry-run/preview mode and merge-not-overwrite on an existing
  `conftest.py` in `quarantine.py`, and artifact storage
  (`memory/known_flakes.md`, `.flake_hunter/`) outside the target repo
  rather than inside it. See "Explicitly deferred" below.
- **Environment for running tests**: no dependency auto-detection
  (rejected — `requirements.txt`/`pyproject.toml`/Poetry/Pipenv/Conda
  are all different conventions, and even this repo doesn't use
  `requirements.txt`). Future external-repo support would take a
  `python_path` config field pointing at an already-working interpreter/
  venv the user provides, not attempt to provision one. Not built now —
  current scope always runs via flake-hunter's own interpreter
  (`sys.executable`), which is already correct for self-analysis.
- **Statistical confidence**: `aggregate()`'s strictly-between-bounds
  rule already can't flag a test with zero observed variation (fail_rate
  strictly between 0 and 1 requires at least one pass and one fail). The
  gap was the *default* `min_fail_rate = 0.0` letting a single fluke
  (1-in-20) count as flaky. Fix: bump the default in `flake_hunter.toml`
  to filter that out, not add new aggregator logic.
- **Crash resilience**: one bad run (subprocess crash, truncated/malformed
  JSON report) must not take down the whole N-run batch. Built into
  Phase 2 directly, not deferred — `runner.py` records a failed
  `RunRecord` instead of raising; `parser.py` skips an unparseable report
  rather than crashing `aggregate()`.

### Explicitly deferred (not this project, or not yet)

- Auto-cloning a repo from a URL, or provisioning its dependencies —
  out of scope by definition, not just deferred. flake-hunter only ever
  targets repos already checked out and already runnable locally.
- `quarantine.py` dry-run/preview mode, existing-`conftest.py` merge
  logic, artifact storage outside the target repo — only matter once a
  second (local) repo is actually pointed at, not for self-analysis.
- `python_path` config field — noted above, not built until multi-repo
  use is actually exercised.
- Schema versioning for `flake_hunter.toml`.
- The former Phase 4/5 harness + CI roadmap, dropped in full except for
  `ARCHITECTURE.md` (kept, see Phase 3): `log-analyzer` subagent,
  `investigate-flaky-test` skill body, adding a GitHub MCP server for
  posting findings to PRs/issues, `.github/workflows/` CI (blocking
  unit-test job + scheduled dogfooding job), and `metrics/runs/`
  wiring.

## Implementation plan

### Phase 2 — core pipeline (branch: `phase-2-core-pipeline`)

- `parser.py`: `parse_run()` reads a `pytest --json-report` file. Per
  test: `outcome` from the `outcome` field, `duration` = sum of
  `setup`/`call`/`teardown` durations, `message` = `call.crash.message`
  (falling back to `setup`/`teardown` if that's where it failed), `None`
  if passed. Malformed/truncated JSON is caught and skips that run
  rather than raising.
- `runner.py`: `run_suite_n_times()` spawns pytest via
  `ThreadPoolExecutor(max_workers=parallel)`, one subprocess per run
  (`sys.executable -m pytest <suite_path> -v --json-report
  --json-report-file=...`), writing stdout+stderr to a log file per run.
  `-v` deliberately, for grep-able per-test PASSED/FAILED lines in the
  logs. Subprocess failures are recorded on the `RunRecord`, not raised.
- `aggregator.py`: `aggregate()` calls `parser.parse_run()` per run,
  tallies pass/fail/error/skip per nodeid, `fail_rate = (fail_count +
  error_count) / total_runs`, flags nodeids strictly between
  `min_fail_rate` and `max_fail_rate`, sorted by nodeid.
- Bump `flake_hunter.toml`'s `min_fail_rate` default above `0.0`.
- Tests (`tests/unit/`): `test_parser.py` / `test_runner.py` via
  pytest's `pytester` fixture (deterministic temp test files, not the
  randomized demo suite); `test_aggregator.py` with monkeypatched
  `parser.parse_run` covering the boundary cases explicitly;
  `test_pipeline_against_fixture.py` — the actual checkpoint: real
  end-to-end run against `flaky_demo_suite`, asserting exactly the 3
  planted flaky tests are flagged and neither control.
- Re-enable `tests` in `pyproject.toml`'s mypy `files`.

### Phase 3 — output modes + orchestration (branch: `phase-3-output-modes`)

- `report.py`: `render_markdown()`.
- `quarantine.py`: `write_known_flakes()` (merge into
  `memory/known_flakes.md`, never overwrite history) and
  `apply_quarantine_marks()` (self-repo only, per scope decision above).
- Wire `cli.py`'s real body: the full
  config → runner → parser → aggregator → report/quarantine chain.
  This is the point at which orchestration is actually proven solved —
  `flake-hunter` runs end-to-end against the demo fixture.
- `ARCHITECTURE.md` — written against real, finished decisions, once
  orchestration is wired and proven end-to-end above.
