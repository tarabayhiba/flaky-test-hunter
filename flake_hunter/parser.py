"""Parse pytest-json-report output into per-test outcomes."""

from __future__ import annotations

from pathlib import Path

from flake_hunter.models import TestOutcome


def parse_run(json_report_path: Path) -> dict[str, TestOutcome]:
    """Parse a single pytest-json-report file into per-test outcomes."""
    raise NotImplementedError
