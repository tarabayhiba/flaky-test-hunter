"""Tests for flake_hunter.config.load_config."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from flake_hunter.config import load_config

_VALID_TOML = """
[suite]
path = "tests/fixtures/flaky_demo_suite"

[run]
runs = 20
parallel = 4
output_dir = ".flake_hunter/raw_runs"

[thresholds]
min_fail_rate = 0.05
max_fail_rate = 1.0

[quarantine]
mode = "report"
"""


def _write(tmp_path: Path, contents: str) -> Path:
    config_path = tmp_path / "flake_hunter.toml"
    config_path.write_text(contents)
    return config_path


def test_load_config_reads_expected_fields(tmp_path: Path) -> None:
    config_path = _write(tmp_path, _VALID_TOML)

    config = load_config(config_path)

    assert config.suite_path == Path("tests/fixtures/flaky_demo_suite")
    assert config.runs == 20
    assert config.parallel == 4
    assert config.output_dir == Path(".flake_hunter/raw_runs")
    assert config.min_fail_rate == pytest.approx(0.05)
    assert config.max_fail_rate == pytest.approx(1.0)
    assert config.quarantine.mode == "report"


@pytest.mark.parametrize("bad_runs", [0, -1])
def test_load_config_rejects_non_positive_runs(tmp_path: Path, bad_runs: int) -> None:
    toml = _VALID_TOML.replace("runs = 20", f"runs = {bad_runs}")
    config_path = _write(tmp_path, toml)

    with pytest.raises(ValueError, match="runs"):
        load_config(config_path)


def test_load_config_rejects_non_positive_parallel(tmp_path: Path) -> None:
    toml = _VALID_TOML.replace("parallel = 4", "parallel = 0")
    config_path = _write(tmp_path, toml)

    with pytest.raises(ValueError, match="parallel"):
        load_config(config_path)


def test_load_config_rejects_min_greater_than_max(tmp_path: Path) -> None:
    toml = _VALID_TOML.replace("min_fail_rate = 0.05", "min_fail_rate = 0.9").replace(
        "max_fail_rate = 1.0", "max_fail_rate = 0.5"
    )
    config_path = _write(tmp_path, toml)

    with pytest.raises(ValueError, match="fail_rate"):
        load_config(config_path)


def test_load_config_rejects_out_of_range_thresholds(tmp_path: Path) -> None:
    toml = _VALID_TOML.replace("max_fail_rate = 1.0", "max_fail_rate = 1.5")
    config_path = _write(tmp_path, toml)

    with pytest.raises(ValueError, match="fail_rate"):
        load_config(config_path)


def test_load_config_rejects_unknown_quarantine_mode(tmp_path: Path) -> None:
    toml = _VALID_TOML.replace('mode = "report"', 'mode = "bogus"')
    config_path = _write(tmp_path, toml)

    with pytest.raises(ValueError, match="mode"):
        load_config(config_path)


def test_load_config_missing_file_raises_oserror(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        load_config(tmp_path / "does_not_exist.toml")


def test_load_config_malformed_toml_propagates(tmp_path: Path) -> None:
    config_path = _write(tmp_path, "this is not [ valid toml")

    with pytest.raises(tomllib.TOMLDecodeError):
        load_config(config_path)
