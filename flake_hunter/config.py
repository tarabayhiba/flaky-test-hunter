"""Load and validate flake_hunter.toml.

This is the user-facing run configuration for the tool itself, kept
separate from pyproject.toml (packaging/tooling config for this repo).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

QuarantineMode = Literal["report", "apply", "both"]
_QUARANTINE_MODES = get_args(QuarantineMode)


@dataclass(frozen=True, slots=True)
class QuarantineConfig:
    mode: QuarantineMode


@dataclass(frozen=True, slots=True)
class FlakeHunterConfig:
    suite_path: Path
    runs: int
    parallel: int
    output_dir: Path
    min_fail_rate: float
    max_fail_rate: float
    quarantine: QuarantineConfig


def load_config(config_path: Path) -> FlakeHunterConfig:
    """Load and validate flake_hunter.toml at ``config_path``.

    Lets ``tomllib.TOMLDecodeError`` (malformed TOML) and ``OSError``
    (missing file) propagate uncaught -- these are user-facing config
    errors, not the "degrade gracefully" pattern used elsewhere in the
    pipeline.
    """
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    runs = raw["run"]["runs"]
    parallel = raw["run"]["parallel"]
    min_fail_rate = raw["thresholds"]["min_fail_rate"]
    max_fail_rate = raw["thresholds"]["max_fail_rate"]
    mode = raw["quarantine"]["mode"]

    if runs <= 0:
        raise ValueError(f"[run].runs must be > 0, got {runs!r}")
    if parallel <= 0:
        raise ValueError(f"[run].parallel must be > 0, got {parallel!r}")
    if not (0.0 <= min_fail_rate <= max_fail_rate <= 1.0):
        raise ValueError(
            "[thresholds].min_fail_rate/max_fail_rate must satisfy "
            f"0.0 <= min_fail_rate <= max_fail_rate <= 1.0, got "
            f"min_fail_rate={min_fail_rate!r}, max_fail_rate={max_fail_rate!r}"
        )
    if mode not in _QUARANTINE_MODES:
        raise ValueError(f"[quarantine].mode must be one of {_QUARANTINE_MODES}, got {mode!r}")

    return FlakeHunterConfig(
        suite_path=Path(raw["suite"]["path"]),
        runs=runs,
        parallel=parallel,
        output_dir=Path(raw["run"]["output_dir"]),
        min_fail_rate=min_fail_rate,
        max_fail_rate=max_fail_rate,
        quarantine=QuarantineConfig(mode=mode),
    )
