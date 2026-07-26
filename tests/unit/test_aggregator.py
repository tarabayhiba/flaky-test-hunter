"""Tests for flake_hunter.aggregator.aggregate.

Uses a monkeypatched parser.parse_run so each boundary case (exactly at a
bound, strictly between bounds, unparseable runs) can be constructed
directly, rather than relying on real pytest subprocess randomness.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from flake_hunter import aggregator
from flake_hunter.models import Outcome, RunManifest, RunRecord, TestOutcome


def _manifest(n: int) -> RunManifest:
    return RunManifest(
        suite_path=Path("suite"),
        output_dir=Path("out"),
        runs=[
            RunRecord(
                run_index=i,
                json_report_path=Path(f"run_{i}.json"),
                log_path=Path(f"run_{i}.log"),
                started_at=datetime.now(),
                duration=0.1,
                exit_code=0,
            )
            for i in range(n)
        ],
    )


def _run_index(path: Path) -> int:
    return int(path.stem.removeprefix("run_"))


def test_aggregate_flags_only_the_strictly_flaky_test(monkeypatch: pytest.MonkeyPatch) -> None:
    """3/10 fails -> flaky; 0/10 and 10/10 -> not flaky."""
    manifest = _manifest(10)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        return {
            "flaky": TestOutcome(
                nodeid="flaky",
                outcome=Outcome.FAILED if i < 3 else Outcome.PASSED,
                duration=0.01,
                message="boom" if i < 3 else None,
            ),
            "always_passes": TestOutcome(
                nodeid="always_passes", outcome=Outcome.PASSED, duration=0.01
            ),
            "always_fails": TestOutcome(
                nodeid="always_fails", outcome=Outcome.FAILED, duration=0.01, message="nope"
            ),
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate(manifest, min_fail_rate=0.0, max_fail_rate=1.0)

    assert [r.nodeid for r in reports] == ["flaky"]
    flaky = reports[0]
    assert flaky.total_runs == 10
    assert flaky.pass_count == 7
    assert flaky.fail_count == 3
    assert flaky.error_count == 0
    assert flaky.skip_count == 0
    assert flaky.fail_rate == pytest.approx(0.3)
    assert flaky.sample_failure_message == "boom"


def test_aggregate_excludes_fail_rate_exactly_at_min_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strictly-between means a fail-rate equal to min_fail_rate is not flaky."""
    manifest = _manifest(10)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        return {
            "borderline": TestOutcome(
                nodeid="borderline",
                outcome=Outcome.FAILED if i < 3 else Outcome.PASSED,
                duration=0.01,
            )
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate(manifest, min_fail_rate=0.3, max_fail_rate=1.0)

    assert reports == []


def test_aggregate_excludes_fail_rate_exactly_at_max_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(10)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        return {
            "borderline": TestOutcome(
                nodeid="borderline",
                outcome=Outcome.FAILED if i < 7 else Outcome.PASSED,
                duration=0.01,
            )
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate(manifest, min_fail_rate=0.0, max_fail_rate=0.7)

    assert reports == []


def test_aggregate_treats_errors_as_failing_for_fail_rate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(4)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        return {
            "errors_sometimes": TestOutcome(
                nodeid="errors_sometimes",
                outcome=Outcome.ERROR if i == 0 else Outcome.PASSED,
                duration=0.01,
            )
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate(manifest, min_fail_rate=0.0, max_fail_rate=1.0)

    assert len(reports) == 1
    assert reports[0].error_count == 1
    assert reports[0].fail_rate == pytest.approx(0.25)


def test_aggregate_skips_are_included_in_total_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(4)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        outcome = Outcome.FAILED if i == 0 else Outcome.SKIPPED if i == 1 else Outcome.PASSED
        return {
            "partly_skipped": TestOutcome(nodeid="partly_skipped", outcome=outcome, duration=0.01)
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate(manifest, min_fail_rate=0.0, max_fail_rate=1.0)

    assert len(reports) == 1
    report = reports[0]
    assert report.total_runs == 4
    assert report.skip_count == 1
    assert report.fail_rate == pytest.approx(0.25)


def test_aggregate_unparseable_runs_contribute_no_observations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(5)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        if i == 0:
            return {}  # simulates a crashed/unparseable run
        return {
            "flaky": TestOutcome(
                nodeid="flaky",
                outcome=Outcome.FAILED if i == 1 else Outcome.PASSED,
                duration=0.01,
            )
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate(manifest, min_fail_rate=0.0, max_fail_rate=1.0)

    assert len(reports) == 1
    # Only the 4 parseable runs count -- not the 5 in the manifest.
    assert reports[0].total_runs == 4
    assert reports[0].fail_rate == pytest.approx(0.25)


def test_aggregate_sample_failure_message_is_first_seen(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(3)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        return {
            "flaky": TestOutcome(
                nodeid="flaky",
                outcome=Outcome.PASSED if i == 0 else Outcome.FAILED,
                duration=0.01,
                message=None if i == 0 else f"failure #{i}",
            )
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate(manifest, min_fail_rate=0.0, max_fail_rate=1.0)

    assert reports[0].sample_failure_message == "failure #1"


def test_aggregate_reports_sorted_by_nodeid(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(4)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        outcome = Outcome.FAILED if i % 2 == 0 else Outcome.PASSED
        return {
            "z_flaky": TestOutcome(nodeid="z_flaky", outcome=outcome, duration=0.01),
            "a_flaky": TestOutcome(nodeid="a_flaky", outcome=outcome, duration=0.01),
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate(manifest, min_fail_rate=0.0, max_fail_rate=1.0)

    assert [r.nodeid for r in reports] == ["a_flaky", "z_flaky"]


def test_aggregate_stable_excludes_genuinely_flaky_test(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(10)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        return {
            "flaky": TestOutcome(
                nodeid="flaky",
                outcome=Outcome.FAILED if i < 3 else Outcome.PASSED,
                duration=0.01,
            )
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate_stable(manifest)

    assert reports == []


def test_aggregate_stable_includes_always_passing_test(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(5)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        return {
            "always_passes": TestOutcome(
                nodeid="always_passes", outcome=Outcome.PASSED, duration=0.01
            )
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate_stable(manifest)

    assert [r.nodeid for r in reports] == ["always_passes"]
    assert reports[0].fail_rate == 0.0


def test_aggregate_stable_includes_always_failing_test(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(5)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        return {
            "always_fails": TestOutcome(
                nodeid="always_fails", outcome=Outcome.FAILED, duration=0.01, message="nope"
            )
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate_stable(manifest)

    assert [r.nodeid for r in reports] == ["always_fails"]
    assert reports[0].fail_rate == 1.0
    assert reports[0].sample_failure_message == "nope"


def test_aggregate_stable_excludes_test_with_any_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(5)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        i = _run_index(path)
        outcome = Outcome.SKIPPED if i == 0 else Outcome.PASSED
        return {
            "partly_skipped": TestOutcome(nodeid="partly_skipped", outcome=outcome, duration=0.01)
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate_stable(manifest)

    assert reports == []


def test_aggregate_stable_reports_sorted_by_nodeid(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(3)

    def fake_parse_run(path: Path) -> dict[str, TestOutcome]:
        return {
            "z_stable": TestOutcome(nodeid="z_stable", outcome=Outcome.PASSED, duration=0.01),
            "a_stable": TestOutcome(nodeid="a_stable", outcome=Outcome.FAILED, duration=0.01),
        }

    monkeypatch.setattr(aggregator, "parse_run", fake_parse_run)

    reports = aggregator.aggregate_stable(manifest)

    assert [r.nodeid for r in reports] == ["a_stable", "z_stable"]
