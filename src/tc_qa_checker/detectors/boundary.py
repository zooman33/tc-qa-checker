"""Cross-run boundary detector.

Word's compare feature stitches insertions and deletions together; when changes are
accepted, the seams can leave doubled words, double spaces, or missing sentence
spacing in the target's accepted text. This detector scans that rendered text.
"""

from __future__ import annotations

import re

from ..models import AlignedPair, Finding, Severity
from .base import PairContext, make_finding, register

# Short words that legitimately repeat in common target languages; not flagged.
DEFAULT_DOUBLED_WORD_STOPWORDS = frozenset({"no", "si", "ya", "ah", "oh", "ha", "he"})

_DOUBLED_WORD_RE = re.compile(r"\b(\w{2,})\s+\1\b", re.IGNORECASE)
_DOUBLE_SPACE_RE = re.compile(r"\S {2,}\S")
_SENTENCE_MERGE_RE = re.compile(r"[a-záéíóúñ][.!?][A-ZÁÉÍÓÚÑ]")


@register("cross_run_boundary", categories=("prose", "bullet"))
def cross_run_boundary(pair: AlignedPair, ctx: PairContext) -> list[Finding]:
    """Detect seam artifacts in the target's accepted text."""
    target = pair.target
    if target is None:
        return []
    text = target.accepted_text or ""
    findings: list[Finding] = []

    for match in _DOUBLED_WORD_RE.finditer(text):
        if match.group(1).lower() in DEFAULT_DOUBLED_WORD_STOPWORDS:
            continue
        findings.append(
            make_finding(
                pair,
                severity=Severity.MAJOR,
                category="Cross-run boundary",
                source="mechanical",
                anchor=match.group(0),
                issue=f'Doubled word detected at TC boundary: "{match.group(0)}"',
                suggestion=(
                    f'Review the phrase around "{match.group(0)}" — likely a stray word at a '
                    "del-to-ins seam"
                ),
            )
        )

    double_space = _DOUBLE_SPACE_RE.search(text)
    if double_space is not None:
        findings.append(
            make_finding(
                pair,
                severity=Severity.MINOR,
                category="Cross-run boundary",
                source="mechanical",
                anchor=double_space.group(0),
                issue="Double space in target accepted text — probably from a del-to-ins seam",
                suggestion=f'Remove extra space: "{double_space.group(0)}"',
            )
        )

    merge = _SENTENCE_MERGE_RE.search(text)
    if merge is not None:
        findings.append(
            make_finding(
                pair,
                severity=Severity.MINOR,
                category="Cross-run boundary",
                source="mechanical",
                anchor=merge.group(0),
                issue="Missing space between sentences in target accepted text",
                suggestion=f'Insert a space at: "{merge.group(0)}"',
            )
        )

    return findings
