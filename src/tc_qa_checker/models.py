"""Core data models shared across the extraction, alignment, and detection stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    """Finding severity, ordered most-to-least serious for sorting and display."""

    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    QUERY = "QUERY"


# Sort rank for severities; unknown values sort last.
SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.MAJOR: 1,
    Severity.MINOR: 2,
    Severity.QUERY: 3,
}


@dataclass
class ParagraphInfo:
    """A single OOXML paragraph and the structural facts the detectors rely on.

    Attributes:
        idx: Zero-based paragraph index in document order.
        accepted: Text with tracked changes accepted (insertions kept, deletions dropped).
        raw: All run text including deleted text, in document order.
        is_list_item: Whether the paragraph carries numbering/bullet properties.
        paragraph_mark_inserted: Whether the paragraph mark itself was inserted.
        ins_count: Count of top-level ``<w:ins>`` runs (excluding the paragraph mark).
        del_count: Count of top-level ``<w:del>`` runs.
        is_in_table_cell: Whether the paragraph lives inside a table cell.
    """

    idx: int
    accepted: str
    raw: str
    is_list_item: bool
    paragraph_mark_inserted: bool
    ins_count: int
    del_count: int
    is_in_table_cell: bool


@dataclass
class TrackChange:
    """A single tracked-change run extracted from a paragraph.

    Attributes:
        change_type: One of ``ins``, ``del``, ``moveFrom``, ``moveTo``.
        text: The run's text content.
        para_idx: Index of the paragraph the change belongs to.
    """

    change_type: str
    text: str
    para_idx: int


@dataclass
class Extraction:
    """The result of parsing one DOCX file."""

    paragraphs: list[ParagraphInfo]
    changes: list[TrackChange]


@dataclass
class ChangeUnit:
    """All tracked changes for one paragraph, grouped for alignment and detection.

    Attributes:
        para_idx: Index of the source paragraph.
        insertion: Concatenated inserted text.
        deletion: Concatenated deleted text.
        move_from: Concatenated move-from text.
        move_to: Concatenated move-to text.
        ins_list: Per-run inserted blocks, preserving block boundaries.
        del_list: Per-run deleted blocks.
        accepted_text: The paragraph's accepted text.
        raw_text: The paragraph's raw text (deletions included).
        is_list_item: Whether the paragraph is a list item.
    """

    para_idx: int
    insertion: str = ""
    deletion: str = ""
    move_from: str = ""
    move_to: str = ""
    ins_list: list[str] = field(default_factory=list)
    del_list: list[str] = field(default_factory=list)
    accepted_text: str = ""
    raw_text: str = ""
    is_list_item: bool = False


@dataclass
class AlignedPair:
    """A source/target pairing produced by unit-level alignment.

    Either side may be ``None`` when alignment leaves a unit unmatched.

    Attributes:
        source: The source-side change unit, if any.
        target: The target-side change unit, if any.
        category: Classification label assigned by :func:`classify`.
    """

    source: ChangeUnit | None
    target: ChangeUnit | None
    category: str = ""


@dataclass
class Finding:
    """A single QA issue raised by a detector.

    Attributes:
        para_idx: Paragraph index the finding is anchored to.
        severity: Severity level.
        category: Human-readable detector category (e.g. ``"Numbers"``).
        source: Origin of the finding (e.g. ``"mechanical"``).
        issue: Description of the problem.
        suggestion: Recommended remediation.
        anchor: Optional matched text snippet that triggered the finding.
        source_del / source_ins: Source-side deleted/inserted text.
        target_del / target_ins: Target-side deleted/inserted text.
        source_accepted / target_accepted: Accepted text on each side.
        status: Review status; defaults to ``"open"``.
    """

    para_idx: int
    severity: Severity
    category: str
    source: str
    issue: str
    suggestion: str
    anchor: str = ""
    source_del: str = ""
    source_ins: str = ""
    target_del: str = ""
    target_ins: str = ""
    source_accepted: str = ""
    target_accepted: str = ""
    status: str = "open"
