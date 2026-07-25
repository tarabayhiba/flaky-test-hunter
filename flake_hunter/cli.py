"""CLI entrypoint: flake-hunter --config flake_hunter.toml [--suite tests/].

Wires config.load_config() -> runner.run_suite_n_times() ->
parser.parse_run() -> aggregator.aggregate() -> report.render_markdown() /
quarantine.write_known_flakes() into one runnable command. Not wired yet --
the modules underneath still raise NotImplementedError.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="flake-hunter")
    parser.add_argument("--config", default="flake_hunter.toml")
    parser.add_argument("--suite", default=None)
    parser.parse_args(argv)
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
