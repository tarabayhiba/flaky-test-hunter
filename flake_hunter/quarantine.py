"""Record and/or enforce quarantine of detected flaky tests.

Dual-mode, controlled by the ``quarantine.mode`` config flag
("report" | "apply" | "both"):

- ``write_known_flakes``: merges findings into memory/known_flakes.md,
  preserving history. Never overwrites prior entries.
- ``apply_quarantine_marks``: writes conftest/marker config into the
  target repo so flagged tests are skipped/xfailed.
"""

from __future__ import annotations

from pathlib import Path

from flake_hunter.models import FlakeReport


def write_known_flakes(reports: list[FlakeReport], known_flakes_path: Path) -> None:
    """Merge newly detected flakes into the known_flakes.md ledger."""
    raise NotImplementedError


def apply_quarantine_marks(reports: list[FlakeReport], target_repo_path: Path) -> None:
    """Write conftest/marker config to skip/xfail flagged tests in the target repo."""
    raise NotImplementedError
