"""Analysis orchestration: ingest two DOCX files and produce QA findings.

Pipeline: extract tracked changes -> group into units -> align units -> classify ->
pair paragraphs (for the drift gate) -> run mechanical sweeps -> de-duplicate.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .alignment import DEFAULT_SKIP_COST, align_units, group_units, pair_paragraphs
from .classification import classify
from .detectors import dedupe_and_sort, run_mechanical_sweeps
from .models import Finding
from .ooxml import extract_track_changes

logger = logging.getLogger(__name__)


def analyze(
    source_bytes: bytes, target_bytes: bytes, *, skip_cost: int = DEFAULT_SKIP_COST
) -> list[Finding]:
    """Analyze a source/target DOCX pair and return QA findings.

    Args:
        source_bytes: Raw bytes of the source ``.docx``.
        target_bytes: Raw bytes of the target ``.docx``.
        skip_cost: Needleman-Wunsch skip cost for unit alignment.

    Returns:
        De-duplicated findings, sorted by paragraph index then severity.
    """
    source = extract_track_changes(source_bytes)
    target = extract_track_changes(target_bytes)
    logger.info(
        "Extracted %d source / %d target paragraphs",
        len(source.paragraphs),
        len(target.paragraphs),
    )

    source_units = group_units(source.changes, source.paragraphs)
    target_units = group_units(target.changes, target.paragraphs)
    logger.info("Grouped %d source / %d target change units", len(source_units), len(target_units))

    pairs = align_units(
        source_units,
        target_units,
        skip_cost,
        len(source.paragraphs),
        len(target.paragraphs),
    )
    for pair in pairs:
        pair.category = classify(pair)

    para_pairing, para_confidence, _anchors = pair_paragraphs(source.paragraphs, target.paragraphs)

    findings = run_mechanical_sweeps(pairs, para_pairing, para_confidence)
    findings = dedupe_and_sort(findings)
    logger.info("Produced %d findings", len(findings))
    return findings


def analyze_files(
    source_path: str | Path, target_path: str | Path, *, skip_cost: int = DEFAULT_SKIP_COST
) -> list[Finding]:
    """Analyze a source/target DOCX pair given file paths.

    Args:
        source_path: Path to the source ``.docx``.
        target_path: Path to the target ``.docx``.
        skip_cost: Needleman-Wunsch skip cost for unit alignment.

    Returns:
        De-duplicated findings, sorted by paragraph index then severity.
    """
    source_bytes = Path(source_path).read_bytes()
    target_bytes = Path(target_path).read_bytes()
    return analyze(source_bytes, target_bytes, skip_cost=skip_cost)
