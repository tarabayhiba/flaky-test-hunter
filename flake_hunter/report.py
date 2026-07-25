"""Render flake reports for human/CI consumption."""

from __future__ import annotations

from flake_hunter.models import FlakeReport


def render_markdown(reports: list[FlakeReport]) -> str:
    """Render flake reports as Markdown, for CLI/CI/PR-comment output."""
    raise NotImplementedError
