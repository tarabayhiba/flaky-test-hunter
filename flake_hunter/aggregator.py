"""Aggregate per-run test outcomes into flakiness reports."""

from __future__ import annotations

from collections import Counter

from flake_hunter.models import FlakeReport, Outcome, RunManifest
from flake_hunter.parser import parse_run

_FAILING = (Outcome.FAILED, Outcome.ERROR)


def aggregate(
    runs: RunManifest,
    min_fail_rate: float,
    max_fail_rate: float,
) -> list[FlakeReport]:
    """Flag tests whose fail-rate falls strictly between the given bounds.

    A fail-rate of exactly 0% or 100% is not flaky -- it's consistently
    passing or consistently failing. A run whose report can't be parsed
    (crashed subprocess, truncated JSON) contributes no observations for
    any nodeid rather than crashing this aggregation.
    """
    tallies: dict[str, Counter[Outcome]] = {}
    sample_failures: dict[str, str] = {}

    for run_record in runs.runs:
        for nodeid, test_outcome in parse_run(run_record.json_report_path).items():
            tallies.setdefault(nodeid, Counter())[test_outcome.outcome] += 1
            if (
                test_outcome.outcome in _FAILING
                and test_outcome.message
                and nodeid not in sample_failures
            ):
                sample_failures[nodeid] = test_outcome.message

    reports: list[FlakeReport] = []
    for nodeid, tally in tallies.items():
        pass_count = tally[Outcome.PASSED]
        fail_count = tally[Outcome.FAILED]
        error_count = tally[Outcome.ERROR]
        skip_count = tally[Outcome.SKIPPED]
        total_runs = pass_count + fail_count + error_count + skip_count
        fail_rate = (fail_count + error_count) / total_runs

        if min_fail_rate < fail_rate < max_fail_rate:
            reports.append(
                FlakeReport(
                    nodeid=nodeid,
                    total_runs=total_runs,
                    pass_count=pass_count,
                    fail_count=fail_count,
                    error_count=error_count,
                    skip_count=skip_count,
                    fail_rate=fail_rate,
                    sample_failure_message=sample_failures.get(nodeid),
                )
            )

    return sorted(reports, key=lambda report: report.nodeid)
