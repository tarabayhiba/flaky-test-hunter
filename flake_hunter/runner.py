"""Run a pytest suite repeatedly and record artifacts to disk."""

from __future__ import annotations

from pathlib import Path

from flake_hunter.models import RunManifest


def run_suite_n_times(
    suite_path: Path,
    runs: int,
    parallel: int,
    output_dir: Path,
) -> RunManifest:
    """Spawn pytest ``runs`` times against ``suite_path``.

    Writes a JSON report and raw console log per run under ``output_dir``
    and returns a manifest of artifact paths. Never returns log or report
    contents directly -- callers read them from disk as needed.
    """
    raise NotImplementedError
