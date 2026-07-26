"""Tests for flake_hunter.report.render_markdown."""

from __future__ import annotations

import re

from flake_hunter.models import FlakeReport
from flake_hunter.report import render_markdown


def _report(
    nodeid: str = "test_sample.py::test_flaky",
    sample_failure_message: str | None = "AssertionError: boom",
) -> FlakeReport:
    return FlakeReport(
        nodeid=nodeid,
        total_runs=20,
        pass_count=17,
        fail_count=3,
        error_count=0,
        skip_count=0,
        fail_rate=0.15,
        sample_failure_message=sample_failure_message,
    )


def test_render_markdown_empty_reports_says_no_flaky_tests() -> None:
    output = render_markdown([])

    assert "no flaky tests" in output.lower()
    assert "|" not in output


def test_render_markdown_includes_nodeid_and_counts() -> None:
    output = render_markdown([_report()])

    assert "test_sample.py::test_flaky" in output
    assert "15.0%" in output
    assert "17" in output
    assert "3" in output
    assert "AssertionError: boom" in output


def test_render_markdown_shows_dash_for_missing_sample_message() -> None:
    output = render_markdown([_report(sample_failure_message=None)])

    lines = [line for line in output.splitlines() if "test_flaky" in line]
    assert len(lines) == 1
    assert lines[0].rstrip().endswith("- |")


def test_render_markdown_sanitizes_embedded_pipe_and_newline() -> None:
    message = "line one\nline two | with a pipe"
    output = render_markdown([_report(sample_failure_message=message)])

    table_line = next(line for line in output.splitlines() if "test_flaky" in line)
    assert table_line.count("\n") == 0
    assert "\\|" in table_line


def test_render_markdown_escapes_pipe_in_nodeid() -> None:
    output = render_markdown([_report(nodeid="test_thing.py::test_thing[a|b]")])

    table_line = next(line for line in output.splitlines() if "test_thing[a" in line)
    assert "test_thing.py::test_thing[a\\|b]" in table_line

    header_line = next(line for line in output.splitlines() if line.startswith("| Test "))
    real_columns_only = re.sub(r"\\\|", "", table_line)
    assert real_columns_only.count("|") == header_line.count("|")


def test_render_markdown_multiple_reports_produces_one_row_each() -> None:
    reports = [
        _report(nodeid="a::test_a"),
        _report(nodeid="b::test_b"),
    ]

    output = render_markdown(reports)

    assert output.count("a::test_a") == 1
    assert output.count("b::test_b") == 1
