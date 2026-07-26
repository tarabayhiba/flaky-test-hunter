"""End-to-end Phase 2 checkpoint: runner -> parser -> aggregator, for real.

Runs the actual flaky_demo_suite fixture through real pytest subprocesses
(no mocking) and checks that aggregate() flags exactly the three
deliberately-flaky tests and neither stable control. This is the ground
truth the whole pipeline is built against -- see
tests/fixtures/flaky_demo_suite/README.md.
"""

from __future__ import annotations

from pathlib import Path

from flake_hunter.aggregator import aggregate
from flake_hunter.runner import run_suite_n_times

_FIXTURE_SUITE = (Path(__file__).parent.parent / "fixtures" / "flaky_demo_suite").resolve()


def test_pipeline_flags_exactly_the_planted_flaky_tests(tmp_path: Path) -> None:
    manifest = run_suite_n_times(
        suite_path=_FIXTURE_SUITE,
        runs=20,
        parallel=4,
        output_dir=tmp_path / "raw_runs",
    )

    reports = aggregate(manifest, min_fail_rate=0.05, max_fail_rate=0.95)

    flagged = {report.nodeid.split("::")[-1] for report in reports}

    assert flagged == {
        "test_flaky_random_coin_flip",
        "test_flaky_shared_temp_race",
        "test_flaky_timing_deadline",
    }
