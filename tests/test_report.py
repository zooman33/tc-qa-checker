"""Tests for finding rendering."""

from __future__ import annotations

import json

from tc_qa_checker.models import Finding, Severity
from tc_qa_checker.report import findings_to_dicts, render_json, render_text


def _finding() -> Finding:
    return Finding(
        para_idx=3,
        severity=Severity.CRITICAL,
        category="Wrong number in target",
        source="mechanical",
        issue="Source INS 35 vs target 28",
        suggestion="Use 35",
        anchor="35",
    )


def test_findings_to_dicts_serializes_severity_as_string() -> None:
    data = findings_to_dicts([_finding()])
    assert data[0]["severity"] == "CRITICAL"
    assert data[0]["category"] == "Wrong number in target"


def test_render_json_is_valid_json() -> None:
    parsed = json.loads(render_json([_finding()]))
    assert parsed[0]["para_idx"] == 3
    assert parsed[0]["severity"] == "CRITICAL"


def test_render_text_includes_summary_and_details() -> None:
    text = render_text([_finding()])
    assert "1 finding(s)" in text
    assert "CRITICAL: 1" in text
    assert "Wrong number in target" in text
    assert "Anchor: 35" in text


def test_render_text_empty() -> None:
    assert render_text([]) == "No issues found."


def test_render_json_empty() -> None:
    assert json.loads(render_json([])) == []
