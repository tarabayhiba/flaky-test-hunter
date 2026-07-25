"""Load and validate flake_hunter.toml.

This is the user-facing run configuration for the tool itself, kept
separate from pyproject.toml (packaging/tooling config for this repo).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

QuarantineMode = Literal["report", "apply", "both"]


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
    """Load and validate flake_hunter.toml at ``config_path``."""
    raise NotImplementedError
