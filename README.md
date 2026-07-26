# flake-hunter

A CLI tool that runs a target pytest suite N times, diffs per-test
outcomes across runs, and flags tests whose fail-rate falls strictly
between two configurable thresholds — 0% and 100% are "consistently
passing/failing," not flaky. Findings can be written to a persistent
Markdown ledger and/or applied as skip/xfail marks in the target repo.

## Why

Flaky tests erode trust in CI: a test that fails 1 run in 5 gets ignored,
re-run, or deleted, and the real bug it's pointing at never gets fixed.
flake-hunter turns "this test feels flaky" into a measured fail-rate
across repeated runs, with a durable record of what's been seen before.

## Install

Requires Python >= 3.11.

```bash
pip install -e ".[dev]"
```

This installs the runtime dependencies (`pytest`, `pytest-json-report`)
plus the dev toolchain (`ruff`, `mypy`, `pre-commit`, `pytest-cov`) and
registers the `flake-hunter` console script.

## Usage

Configure a run in a TOML file (see `flake_hunter.toml` for a working
example against this repo's own demo fixture):

```toml
[suite]
path = "tests/fixtures/flaky_demo_suite"

[run]
runs = 20
parallel = 4
output_dir = ".flake_hunter/raw_runs"

[thresholds]
min_fail_rate = 0.05
max_fail_rate = 1.0

[quarantine]
mode = "report"  # "report" | "apply" | "both"
```

Then run:

```bash
flake-hunter --config flake_hunter.toml
# or override the target suite for one run:
flake-hunter --config flake_hunter.toml --suite path/to/other/suite
```

Depending on `[quarantine].mode`:
- `report` — prints a Markdown flakiness table to stdout and merges
  findings into `memory/known_flakes.md`.
- `apply` — writes skip/xfail marks into the target repo's `conftest.py`
  so flagged tests are quarantined on their next run there.
- `both` — does both of the above.

## Commands

```bash
# Build / install (editable, with dev tools)
pip install -e ".[dev]"

# Run flake-hunter itself, against the config's configured suite
flake-hunter --config flake_hunter.toml

# Run this repo's own unit suite (tests/unit/ only)
pytest

# Run a single test
pytest tests/unit/test_aggregator.py::test_name -v

# Lint / format / type-check
ruff check .
ruff format .
mypy .

# Full local gate (ruff + mypy, pinned to .venv versions) — also runs
# automatically before every `git commit` via a pre-commit hook
.venv/bin/pre-commit run --all-files
```

On this project's dev machine, prefix any of the pytest/mypy commands
above with `env -u PYTHONPATH` — see the gotcha below.

## Local environment gotcha

If you're on a machine with a sourced ROS2 `setup.bash`, its
`PYTHONPATH` leaks into every venv and breaks pytest's plugin autoload
(`ModuleNotFoundError: lark`). Prefix commands with `env -u PYTHONPATH`
if you hit that — it's not a project bug. See `CLAUDE.md` for the full
list of affected commands.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the pipeline, module
responsibilities, and the key design decisions behind them.
