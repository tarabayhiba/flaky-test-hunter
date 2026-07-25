"""Shared typed data containers used across flake_hunter modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class Outcome(StrEnum):
    """A single test's result for a single run, per pytest's own vocabulary."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class TestOutcome:
    """One test node's outcome within a single pytest invocation."""

    nodeid: str
    outcome: Outcome
    duration: float
    message: str | None = None


@dataclass(frozen=True, slots=True)
class RunRecord:
    """On-disk artifact paths for one pytest invocation, not their contents."""

    run_index: int
    json_report_path: Path
    log_path: Path
    started_at: datetime
    duration: float
    exit_code: int


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Paths to the artifacts of a batch of pytest runs.

    Deliberately holds no log or report contents -- callers read those lazily
    from disk (or hand the directory to a subagent) rather than pulling
    potentially thousands of lines into memory at once.
    """

    suite_path: Path
    output_dir: Path
    runs: list[RunRecord] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FlakeReport:
    """Aggregated flakiness stats for one test node across a run batch."""

    nodeid: str
    total_runs: int
    pass_count: int
    fail_count: int
    error_count: int
    skip_count: int
    fail_rate: float
    sample_failure_message: str | None = None
