"""Tests for flake_hunter.parser.parse_run."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from flake_hunter.aggregator import aggregate
from flake_hunter.models import Outcome, RunManifest, RunRecord
from flake_hunter.parser import parse_run


def test_parse_run_reads_passed_and_failed_outcomes(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        test_sample="""
        def test_pass():
            assert True

        def test_fail():
            assert False, "boom"
        """
    )
    report_path = pytester.path / "report.json"
    pytester.runpytest("--json-report", f"--json-report-file={report_path}")

    outcomes = parse_run(report_path)

    assert set(outcomes) == {"test_sample.py::test_pass", "test_sample.py::test_fail"}

    passed = outcomes["test_sample.py::test_pass"]
    assert passed.outcome is Outcome.PASSED
    assert passed.message is None
    assert passed.duration >= 0

    failed = outcomes["test_sample.py::test_fail"]
    assert failed.outcome is Outcome.FAILED
    assert failed.message is not None
    assert "boom" in failed.message
    assert failed.duration >= 0


def test_parse_run_missing_file_returns_empty(tmp_path: Path) -> None:
    assert parse_run(tmp_path / "does_not_exist.json") == {}


def test_parse_run_malformed_json_returns_empty(tmp_path: Path) -> None:
    bad_report = tmp_path / "bad.json"
    bad_report.write_text("{not valid json")

    assert parse_run(bad_report) == {}


def test_parse_run_empty_tests_list_returns_empty(tmp_path: Path) -> None:
    report = tmp_path / "empty.json"
    report.write_text('{"tests": []}')

    assert parse_run(report) == {}


@pytest.mark.parametrize(
    "report_content",
    [
        "[]",
        '"hello"',
        "null",
        '{"tests": null}',
        '{"tests": "oops"}',
        '{"tests": [123, null, "abc"]}',
    ],
)
def test_parse_run_malformed_shape_returns_empty(tmp_path: Path, report_content: str) -> None:
    """Well-formed JSON that isn't shaped like a pytest-json-report must
    still degrade to "no data" rather than raising -- e.g. AttributeError
    from calling .get() on a non-dict, or TypeError from iterating a
    non-list "tests" value.
    """
    report = tmp_path / "malformed.json"
    report.write_text(report_content)

    assert parse_run(report) == {}


def test_parse_run_malformed_report_does_not_crash_batch_aggregation(
    tmp_path: Path,
) -> None:
    """A single malformed report in a batch must not raise out of
    aggregate() -- it should just contribute no observations, leaving the
    other (good) runs' data intact.
    """
    good_report = tmp_path / "good.json"
    good_report.write_text(
        '{"tests": [{"nodeid": "t::test_flaky", "outcome": "failed", '
        '"call": {"duration": 0.01, "crash": {"message": "boom"}}}]}'
    )
    bad_report = tmp_path / "bad.json"
    bad_report.write_text('{"tests": "oops"}')
    good_report_2 = tmp_path / "good2.json"
    good_report_2.write_text(
        '{"tests": [{"nodeid": "t::test_flaky", "outcome": "passed", "call": {"duration": 0.01}}]}'
    )

    manifest = RunManifest(
        suite_path=tmp_path,
        output_dir=tmp_path,
        runs=[
            RunRecord(
                run_index=0,
                json_report_path=good_report,
                log_path=tmp_path / "run_0.log",
                started_at=datetime.now(),
                duration=0.1,
                exit_code=0,
            ),
            RunRecord(
                run_index=1,
                json_report_path=bad_report,
                log_path=tmp_path / "run_1.log",
                started_at=datetime.now(),
                duration=0.1,
                exit_code=0,
            ),
            RunRecord(
                run_index=2,
                json_report_path=good_report_2,
                log_path=tmp_path / "run_2.log",
                started_at=datetime.now(),
                duration=0.1,
                exit_code=0,
            ),
        ],
    )

    reports = aggregate(manifest, min_fail_rate=0.0, max_fail_rate=1.0)

    assert len(reports) == 1
    assert reports[0].nodeid == "t::test_flaky"
    assert reports[0].total_runs == 2
    assert reports[0].fail_count == 1
    assert reports[0].pass_count == 1
