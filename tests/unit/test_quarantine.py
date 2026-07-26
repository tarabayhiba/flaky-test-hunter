"""Tests for flake_hunter.quarantine."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from flake_hunter.models import FlakeReport
from flake_hunter.quarantine import (
    _atomic_write_text,
    apply_quarantine_marks,
    load_marks,
    write_known_flakes,
)


def _report(nodeid: str, pass_count: int, fail_count: int, fail_rate: float) -> FlakeReport:
    return FlakeReport(
        nodeid=nodeid,
        total_runs=pass_count + fail_count,
        pass_count=pass_count,
        fail_count=fail_count,
        error_count=0,
        skip_count=0,
        fail_rate=fail_rate,
    )


def test_write_known_flakes_creates_fresh_ledger(tmp_path: Path) -> None:
    ledger_path = tmp_path / "known_flakes.md"
    reports = [_report("test_a.py::test_flaky", pass_count=17, fail_count=3, fail_rate=0.15)]

    write_known_flakes(reports, ledger_path)

    contents = ledger_path.read_text()
    assert "test_a.py::test_flaky" in contents
    assert "17" in contents
    assert "3" in contents
    assert "unknown" in contents
    assert "flaky" in contents


def test_write_known_flakes_merges_without_dropping_history(tmp_path: Path) -> None:
    ledger_path = tmp_path / "known_flakes.md"

    write_known_flakes(
        [
            _report("test_a.py::test_one", pass_count=17, fail_count=3, fail_rate=0.15),
            _report("test_a.py::test_two", pass_count=10, fail_count=10, fail_rate=0.5),
        ],
        ledger_path,
    )
    first_contents = ledger_path.read_text()
    first_seen_line = next(line for line in first_contents.splitlines() if "test_one" in line)

    write_known_flakes(
        [_report("test_a.py::test_one", pass_count=15, fail_count=5, fail_rate=0.25)],
        ledger_path,
    )
    second_contents = ledger_path.read_text()

    assert "test_two" in second_contents
    updated_line = next(line for line in second_contents.splitlines() if "test_one" in line)
    assert " 15 " in updated_line
    assert " 5 " in updated_line
    first_seen = first_seen_line.split("|")[2].strip()
    assert first_seen in updated_line


def test_write_known_flakes_round_trips_nodeid_containing_pipe(tmp_path: Path) -> None:
    ledger_path = tmp_path / "known_flakes.md"
    nodeid = "test_a.py::test_thing[a|b]"

    write_known_flakes(
        [_report(nodeid, pass_count=17, fail_count=3, fail_rate=0.15)],
        ledger_path,
    )
    write_known_flakes(
        [_report(nodeid, pass_count=15, fail_count=5, fail_rate=0.25)],
        ledger_path,
    )

    contents = ledger_path.read_text()
    matching_lines = [line for line in contents.splitlines() if "test_thing[a" in line]
    assert len(matching_lines) == 1
    assert nodeid in matching_lines[0].replace("\\|", "|")
    assert " 15 " in matching_lines[0]
    assert " 5 " in matching_lines[0]


def test_write_known_flakes_preserves_row_with_malformed_count(tmp_path: Path) -> None:
    ledger_path = tmp_path / "known_flakes.md"
    ledger_path.write_text(
        "# Known Flakes\n\n"
        "| Test ID | First Seen | Pass Count | Fail Count | Suspected Cause | Status |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| test_a.py::test_hand_edited | 2024-01-01 | N/A | 3 | unknown | flaky |\n"
    )

    write_known_flakes(
        [_report("test_a.py::test_new", pass_count=17, fail_count=3, fail_rate=0.15)],
        ledger_path,
    )

    contents = ledger_path.read_text()
    assert "test_hand_edited" in contents
    assert "test_new" in contents


def test_apply_quarantine_marks_rewrites_conftest_with_only_sentinel(tmp_path: Path) -> None:
    conftest_path = tmp_path / "conftest.py"
    conftest_path.write_text("# --- flake-hunter quarantine marks ---\n")

    apply_quarantine_marks(
        [_report("test_a.py::test_one", pass_count=18, fail_count=2, fail_rate=0.1)],
        target_repo_path=tmp_path,
    )

    contents = conftest_path.read_text()
    assert "pytest_collection_modifyitems" in contents


def test_apply_quarantine_marks_writes_json_and_conftest(tmp_path: Path) -> None:
    reports = [
        _report("test_a.py::test_low_fail", pass_count=18, fail_count=2, fail_rate=0.1),
        _report("test_a.py::test_high_fail", pass_count=5, fail_count=15, fail_rate=0.75),
    ]

    apply_quarantine_marks(reports, target_repo_path=tmp_path)

    marks_path = tmp_path / ".flake_hunter" / "quarantine_marks.json"
    marks = json.loads(marks_path.read_text())
    assert marks == {
        "test_a.py::test_low_fail": "skip",
        "test_a.py::test_high_fail": "xfail",
    }

    conftest_contents = (tmp_path / "conftest.py").read_text()
    assert conftest_contents.count("# --- flake-hunter quarantine marks ---") == 1
    assert "pytest_collection_modifyitems" in conftest_contents


def test_apply_quarantine_marks_is_idempotent_on_conftest(tmp_path: Path) -> None:
    apply_quarantine_marks(
        [_report("test_a.py::test_one", pass_count=18, fail_count=2, fail_rate=0.1)],
        target_repo_path=tmp_path,
    )
    apply_quarantine_marks(
        [_report("test_a.py::test_two", pass_count=10, fail_count=10, fail_rate=0.5)],
        target_repo_path=tmp_path,
    )

    conftest_contents = (tmp_path / "conftest.py").read_text()
    assert conftest_contents.count("# --- flake-hunter quarantine marks ---") == 1

    marks_path = tmp_path / ".flake_hunter" / "quarantine_marks.json"
    marks = json.loads(marks_path.read_text())
    assert marks == {"test_a.py::test_two": "xfail"}


def test_apply_quarantine_marks_appends_to_existing_conftest(tmp_path: Path) -> None:
    conftest_path = tmp_path / "conftest.py"
    conftest_path.write_text("# unrelated existing conftest content\n")

    apply_quarantine_marks(
        [_report("test_a.py::test_one", pass_count=18, fail_count=2, fail_rate=0.1)],
        target_repo_path=tmp_path,
    )

    contents = conftest_path.read_text()
    assert "unrelated existing conftest content" in contents
    assert "# --- flake-hunter quarantine marks ---" in contents


def test_apply_quarantine_marks_appends_after_real_code_compiles(tmp_path: Path) -> None:
    conftest_path = tmp_path / "conftest.py"
    conftest_path.write_text("import sys\n")

    apply_quarantine_marks(
        [_report("test_a.py::test_one", pass_count=18, fail_count=2, fail_rate=0.1)],
        target_repo_path=tmp_path,
    )

    contents = conftest_path.read_text()
    assert "import sys" in contents
    compile(contents, str(conftest_path), "exec")


def test_atomic_write_text_preserves_existing_file_mode(tmp_path: Path) -> None:
    target = tmp_path / "known_flakes.md"
    target.write_text("original\n")
    target.chmod(0o644)

    _atomic_write_text(target, "replaced\n")

    assert stat.S_IMODE(target.stat().st_mode) == 0o644


def test_atomic_write_text_applies_umask_appropriate_mode_for_fresh_file(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "known_flakes.md"
    test_umask = 0o022
    old_umask = os.umask(test_umask)
    try:
        write_known_flakes(
            [_report("test_a.py::test_flaky", pass_count=17, fail_count=3, fail_rate=0.15)],
            ledger_path,
        )
    finally:
        os.umask(old_umask)

    assert stat.S_IMODE(ledger_path.stat().st_mode) == 0o666 & ~test_umask


def test_load_marks_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert load_marks(tmp_path) == {}


def test_load_marks_returns_empty_for_malformed_json(tmp_path: Path) -> None:
    marks_dir = tmp_path / ".flake_hunter"
    marks_dir.mkdir()
    (marks_dir / "quarantine_marks.json").write_bytes(b"{not valid json")

    assert load_marks(tmp_path) == {}


def test_load_marks_round_trips_with_apply_quarantine_marks(tmp_path: Path) -> None:
    apply_quarantine_marks(
        [_report("test_a.py::test_one", pass_count=18, fail_count=2, fail_rate=0.1)],
        target_repo_path=tmp_path,
    )

    assert load_marks(tmp_path) == {"test_a.py::test_one": "skip"}
