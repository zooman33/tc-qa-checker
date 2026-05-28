"""Mechanical detector pipeline.

Importing this package registers the built-in detectors. :func:`run_mechanical_sweeps`
runs them per pair, honoring the pre-TOC schedule and TOC suppression, and
:func:`dedupe_and_sort` finalizes the findings list.
"""

from __future__ import annotations

from ..classification import TOC_NUM, TOC_SECTION, looks_like_toc_entry
from ..models import SEVERITY_ORDER, AlignedPair, Finding
from . import boundary, completeness, numbers  # noqa: F401  (import triggers registration)
from .base import Detector, PairContext, make_finding, register, registry

__all__ = [
    "Detector",
    "PairContext",
    "dedupe_and_sort",
    "make_finding",
    "register",
    "registry",
    "run_mechanical_sweeps",
]


def run_mechanical_sweeps(
    pairs: list[AlignedPair],
    para_pairing: dict[int, int | None],
    para_confidence: dict[int, str],
) -> list[Finding]:
    """Run every registered detector across all aligned pairs.

    Args:
        pairs: Aligned source/target pairs with ``category`` already assigned.
        para_pairing: Paragraph-level pairing used by the alignment-drift gate.
        para_confidence: Paragraph-level pairing confidence.

    Returns:
        All findings produced, before de-duplication.
    """
    detectors = registry()
    pre_toc = [d for d in detectors if d.pre_toc]
    post_toc = [d for d in detectors if not d.pre_toc]

    findings: list[Finding] = []
    for pair in pairs:
        if pair.source is None or pair.target is None:
            continue
        ctx = PairContext(para_pairing=para_pairing, para_confidence=para_confidence)

        for detector in pre_toc:
            findings.extend(detector.func(pair, ctx))

        if pair.category in (TOC_NUM, TOC_SECTION):
            continue
        if looks_like_toc_entry(pair.source.accepted_text) or looks_like_toc_entry(
            pair.target.accepted_text
        ):
            continue

        for detector in post_toc:
            if detector.categories is not None and pair.category not in detector.categories:
                continue
            findings.extend(detector.func(pair, ctx))

    return findings


def dedupe_and_sort(findings: list[Finding]) -> list[Finding]:
    """De-duplicate findings and sort by paragraph index then severity."""
    seen: dict[tuple[int, str, str, str], Finding] = {}
    for finding in findings:
        key = (
            finding.para_idx,
            finding.category,
            finding.anchor[:30],
            finding.issue[:50],
        )
        if key not in seen:
            seen[key] = finding
    return sorted(
        seen.values(),
        key=lambda f: (f.para_idx, SEVERITY_ORDER.get(f.severity, 9)),
    )
