"""CLI entrypoint: flake-hunter --config flake_hunter.toml [--suite tests/].

Wires config.load_config() -> runner.run_suite_n_times() ->
parser.parse_run() -> aggregator.aggregate() / aggregate_stable() ->
report.render_markdown() / quarantine.write_known_flakes() into one
runnable command. Only the flaky reports go to render_markdown() and
apply_quarantine_marks() (those are about flagging problems); both flaky
and stable/always-failing reports go to write_known_flakes() (the ledger
tracks every test's status, not just flaky ones).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from flake_hunter import quarantine, report
from flake_hunter.aggregator import aggregate, aggregate_stable
from flake_hunter.config import load_config
from flake_hunter.runner import run_suite_n_times

_KNOWN_FLAKES_PATH = Path("memory/known_flakes.md")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="flake-hunter")
    parser.add_argument("--config", default="flake_hunter.toml")
    parser.add_argument("--suite", default=None)
    args = parser.parse_args(argv)

    try:
        config = load_config(Path(args.config))
        if args.suite is not None:
            config = replace(config, suite_path=Path(args.suite))

        manifest = run_suite_n_times(
            suite_path=config.suite_path,
            runs=config.runs,
            parallel=config.parallel,
            output_dir=config.output_dir,
        )
        reports = aggregate(manifest, config.min_fail_rate, config.max_fail_rate)
        stable_reports = aggregate_stable(manifest)

        mode = config.quarantine.mode
        if mode in ("report", "both"):
            print(report.render_markdown(reports))
            quarantine.write_known_flakes(reports + stable_reports, _KNOWN_FLAKES_PATH)
        if mode in ("apply", "both"):
            quarantine.apply_quarantine_marks(reports, target_repo_path=config.suite_path)
    except Exception as exc:
        print(f"flake-hunter: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
