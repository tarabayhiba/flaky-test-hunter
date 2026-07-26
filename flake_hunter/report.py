"""Render flake reports for human/CI consumption."""

from __future__ import annotations

from flake_hunter.models import FlakeReport

_MAX_MESSAGE_LEN = 80


def _escape_pipes(text: str) -> str:
    return text.replace("|", "\\|")


def _sanitize_message(message: str | None) -> str:
    if message is None:
        return "-"
    single_line = " ".join(message.split())
    single_line = _escape_pipes(single_line)
    if len(single_line) > _MAX_MESSAGE_LEN:
        single_line = single_line[: _MAX_MESSAGE_LEN - 1] + "…"
    return single_line


def render_markdown(reports: list[FlakeReport]) -> str:
    """Render flake reports as Markdown, for CLI/CI/PR-comment output."""
    if not reports:
        return "No flaky tests found.\n"

    lines = [
        "| Test | Fail rate | Pass | Fail | Error | Skip | Sample failure |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for report in reports:
        lines.append(
            f"| {_escape_pipes(report.nodeid)} | {report.fail_rate:.1%} | {report.pass_count} | "
            f"{report.fail_count} | {report.error_count} | {report.skip_count} | "
            f"{_sanitize_message(report.sample_failure_message)} |"
        )
    return "\n".join(lines) + "\n"
