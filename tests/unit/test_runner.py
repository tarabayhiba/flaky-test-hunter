"""Tests for flake_hunter.runner.run_suite_n_times."""

from __future__ import annotations

from pathlib import Path

import pytest

from flake_hunter.parser import parse_run
from flake_hunter.runner import run_suite_n_times


def test_run_suite_n_times_writes_manifest_and_artifacts(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    pytester.makepyfile(
        test_sample="""
        def test_always_passes():
            assert True
        """
    )
    output_dir = tmp_path / "raw_runs"

    manifest = run_suite_n_times(
        suite_path=pytester.path,
        runs=3,
        parallel=2,
        output_dir=output_dir,
    )

    assert manifest.suite_path == pytester.path
    assert manifest.output_dir == output_dir
    assert len(manifest.runs) == 3
    assert {record.run_index for record in manifest.runs} == {0, 1, 2}

    for record in manifest.runs:
        assert record.exit_code == 0
        assert record.json_report_path.exists()
        assert record.log_path.exists()
        assert record.duration >= 0

        outcomes = parse_run(record.json_report_path)
        assert "test_sample.py::test_always_passes" in outcomes


def test_run_suite_n_times_records_failure_without_raising(tmp_path: Path) -> None:
    missing_suite = tmp_path / "does_not_exist"
    output_dir = tmp_path / "raw_runs"

    manifest = run_suite_n_times(
        suite_path=missing_suite,
        runs=2,
        parallel=2,
        output_dir=output_dir,
    )

    assert len(manifest.runs) == 2
    for record in manifest.runs:
        assert record.exit_code != 0
        assert record.log_path.exists()


def test_run_suite_n_times_returns_promptly_on_hanging_test(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    """A test that hangs past ``timeout`` must not block the whole batch
    forever -- the run is killed and recorded as a failed RunRecord.
    """
    pytester.makepyfile(
        test_sample="""
        import time

        def test_hangs():
            time.sleep(3600)
        """
    )
    output_dir = tmp_path / "raw_runs"

    manifest = run_suite_n_times(
        suite_path=pytester.path,
        runs=1,
        parallel=1,
        output_dir=output_dir,
        timeout=2.0,
    )

    assert len(manifest.runs) == 1
    record = manifest.runs[0]
    assert record.exit_code != 0
    assert record.log_path.exists()
    assert "timed out" in record.log_path.read_text()
    assert record.duration < 60
