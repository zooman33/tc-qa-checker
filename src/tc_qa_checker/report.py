"""Rendering of findings to JSON and human-readable text."""

from __future__ import annotations

import json
from dataclasses import asdict

from .models import Finding


def findings_to_dicts(findings: list[Finding]) -> list[dict[str, object]]:
    """Convert findings to plain dictionaries with the severity as a string."""
    result: list[dict[str, object]] = []
    for finding in findings:
        data = asdict(finding)
        data["severity"] = finding.severity.value
        result.append(data)
    return result


def render_json(findings: list[Finding], *, indent: int = 2) -> str:
    """Render findings as a JSON array."""
    return json.dumps(findings_to_dicts(findings), indent=indent, ensure_ascii=False)


def render_text(findings: list[Finding]) -> str:
    """Render findings as a readable plain-text report."""
    if not findings:
        return "No issues found."

    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity.value] = counts.get(finding.severity.value, 0) + 1
    summary = " · ".join(f"{sev}: {n}" for sev, n in counts.items())

    lines = [f"{len(findings)} finding(s) — {summary}", ""]
    for finding in findings:
        lines.append(
            f"[{finding.severity.value}] {finding.category} (paragraph {finding.para_idx})"
        )
        lines.append(f"  Issue: {finding.issue}")
        lines.append(f"  Suggestion: {finding.suggestion}")
        if finding.anchor:
            lines.append(f"  Anchor: {finding.anchor}")
        lines.append("")
    return "\n".join(lines).rstrip()
