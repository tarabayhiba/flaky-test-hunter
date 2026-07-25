"""Aggregate per-run test outcomes into flakiness reports."""

from __future__ import annotations

from flake_hunter.models import FlakeReport, RunManifest


def aggregate(
    runs: RunManifest,
    min_fail_rate: float,
    max_fail_rate: float,
) -> list[FlakeReport]:
    """Flag tests whose fail-rate falls strictly between the given bounds.

    A fail-rate of exactly 0% or 100% is not flaky -- it's consistently
    passing or consistently failing.
    """
    raise NotImplementedError
