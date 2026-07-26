"""Aggregate per-run test outcomes into flakiness reports."""

from __future__ import annotations

from collections import Counter

from flake_hunter.models import FlakeReport, Outcome, RunManifest
from flake_hunter.parser import parse_run

_FAILING = (Outcome.FAILED, Outcome.ERROR)


def _build_tallies(
    runs: RunManifest,
) -> tuple[dict[str, Counter[Outcome]], dict[str, str]]:
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

    return tallies, sample_failures


def _build_report(
    nodeid: str, tally: Counter[Outcome], sample_failures: dict[str, str]
) -> FlakeReport:
    pass_count = tally[Outcome.PASSED]
    fail_count = tally[Outcome.FAILED]
    error_count = tally[Outcome.ERROR]
    skip_count = tally[Outcome.SKIPPED]
    total_runs = pass_count + fail_count + error_count + skip_count
    fail_rate = (fail_count + error_count) / total_runs

    return FlakeReport(
        nodeid=nodeid,
        total_runs=total_runs,
        pass_count=pass_count,
        fail_count=fail_count,
        error_count=error_count,
        skip_count=skip_count,
        fail_rate=fail_rate,
        sample_failure_message=sample_failures.get(nodeid),
    )


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
    tallies, sample_failures = _build_tallies(runs)

    reports = [_build_report(nodeid, tally, sample_failures) for nodeid, tally in tallies.items()]
    reports = [report for report in reports if min_fail_rate < report.fail_rate < max_fail_rate]

    return sorted(reports, key=lambda report: report.nodeid)


def aggregate_stable(runs: RunManifest) -> list[FlakeReport]:
    """Identify tests with a unanimous outcome across every observed run.

    A "stable" test passed every observed run; an "always-failing" test
    failed/errored every observed run. Both are non-flaky by
    ``aggregate()``'s strict-inequality rule, but they aren't the same
    thing -- distinguishing between them is left to the caller
    (``quarantine.write_known_flakes``, which derives the ledger status
    from ``fail_rate``). This function's job is only to identify the
    unanimous-outcome nodeids: those with ``fail_rate`` of exactly 0.0 or
    exactly 1.0. A test with any skips in the batch, or a non-unanimous
    split, is excluded entirely -- it's either flaky, or ambiguous, and
    left alone rather than shoehorned into either bucket.
    """
    tallies, sample_failures = _build_tallies(runs)

    reports = [_build_report(nodeid, tally, sample_failures) for nodeid, tally in tallies.items()]
    reports = [
        report for report in reports if report.skip_count == 0 and report.fail_rate in (0.0, 1.0)
    ]

    return sorted(reports, key=lambda report: report.nodeid)
