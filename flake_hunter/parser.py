"""Parse pytest-json-report output into per-test outcomes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flake_hunter.models import Outcome, TestOutcome

_PHASES = ("setup", "call", "teardown")


def parse_run(json_report_path: Path) -> dict[str, TestOutcome]:
    """Parse a single pytest-json-report file into per-test outcomes.

    Returns an empty mapping if the report is missing, truncated, or
    otherwise unparseable -- a bad run degrades to "no data" for its
    nodeids rather than raising, so a single crashed run can't take down
    a whole batch aggregation.
    """
    try:
        raw: Any = json.loads(json_report_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw, dict):
        return {}

    tests = raw.get("tests")
    if not isinstance(tests, list):
        return {}

    outcomes: dict[str, TestOutcome] = {}
    for test in tests:
        if not isinstance(test, dict):
            continue
        nodeid = test.get("nodeid")
        outcome_str = test.get("outcome")
        if nodeid is None or outcome_str is None:
            continue
        try:
            outcome = Outcome(outcome_str)
        except ValueError:
            continue

        duration = sum(test.get(phase, {}).get("duration", 0.0) for phase in _PHASES)

        message: str | None = None
        for phase in ("call", "setup", "teardown"):
            crash = test.get(phase, {}).get("crash")
            if crash:
                message = crash.get("message")
                break

        outcomes[nodeid] = TestOutcome(
            nodeid=nodeid,
            outcome=outcome,
            duration=duration,
            message=message,
        )
    return outcomes
