"""End-to-end test for flake_hunter.cli.main.

Runs the real pipeline (config -> runner -> aggregator -> report/
quarantine) against the flaky_demo_suite fixture, same ground truth as
test_pipeline_against_fixture.py. Exercises cli.py's wiring, not the
underlying modules' internals (already covered elsewhere).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flake_hunter import cli

_FIXTURE_SUITE = (Path(__file__).parent.parent / "fixtures" / "flaky_demo_suite").resolve()

_EXPECTED_FLAKY_TESTS = {
    "test_flaky_random_coin_flip",
    "test_flaky_shared_temp_race",
    "test_flaky_timing_deadline",
}


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "flake_hunter.toml"
    output_dir = tmp_path / "raw_runs"
    config_path.write_text(
        f"""
[suite]
path = "{_FIXTURE_SUITE}"

[run]
runs = 20
parallel = 4
output_dir = "{output_dir}"

[thresholds]
min_fail_rate = 0.05
max_fail_rate = 1.0

[quarantine]
mode = "report"
"""
    )
    return config_path


def test_cli_main_reports_the_planted_flaky_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """cli.py hardcodes the known-flakes ledger at memory/known_flakes.md
    relative to cwd (per the task brief's stated default) -- chdir into
    tmp_path so this test doesn't write into the real repo's ledger.
    """
    monkeypatch.chdir(tmp_path)
    config_path = _write_config(tmp_path)

    exit_code = cli.main(["--config", str(config_path)])

    assert exit_code == 0

    stdout = capsys.readouterr().out
    for test_name in _EXPECTED_FLAKY_TESTS:
        assert test_name in stdout

    ledger_path = tmp_path / "memory" / "known_flakes.md"
    assert ledger_path.exists()
    ledger_contents = ledger_path.read_text()
    for test_name in _EXPECTED_FLAKY_TESTS:
        assert test_name in ledger_contents

    stable_line = next(
        line for line in ledger_contents.splitlines() if "test_always_passes" in line
    )
    assert "| stable |" in stable_line
    always_failing_line = next(
        line for line in ledger_contents.splitlines() if "test_always_fails" in line
    )
    assert "| always-failing |" in always_failing_line


def test_cli_main_returns_nonzero_on_bad_config(tmp_path: Path) -> None:
    config_path = tmp_path / "flake_hunter.toml"
    config_path.write_text("[run]\nruns = 0\n")

    exit_code = cli.main(["--config", str(config_path)])

    assert exit_code == 1


def test_cli_main_apply_mode_writes_marks_inside_suite_path_not_its_parent(
    tmp_path: Path,
) -> None:
    """Regression test: apply_quarantine_marks must be called with
    config.suite_path itself, not its parent, so quarantine artifacts land
    inside the target suite directory rather than one level above it.
    """
    suite_path = tmp_path / "target_repo"
    suite_path.mkdir()
    (suite_path / "test_stub.py").write_text("def test_always_passes() -> None:\n    assert True\n")
    output_dir = tmp_path / "raw_runs"

    config_path = tmp_path / "flake_hunter.toml"
    config_path.write_text(
        f"""
[suite]
path = "{suite_path}"

[run]
runs = 2
parallel = 1
output_dir = "{output_dir}"

[thresholds]
min_fail_rate = 0.05
max_fail_rate = 1.0

[quarantine]
mode = "apply"
"""
    )

    exit_code = cli.main(["--config", str(config_path)])

    assert exit_code == 0
    assert (suite_path / "conftest.py").exists()
    assert (suite_path / ".flake_hunter" / "quarantine_marks.json").exists()
    assert not (tmp_path / "conftest.py").exists()
    assert not (tmp_path / ".flake_hunter" / "quarantine_marks.json").exists()
