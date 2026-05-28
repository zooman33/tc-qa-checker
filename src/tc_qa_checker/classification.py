"""Classification of aligned pairs and a table-of-contents heuristic.

Classification routes each pair to a category that gates which detectors run.
The TOC heuristic suppresses false positives on contents-list entries, whose
page numbers are auto-regenerated and never hand-edited by a linguist.
"""

from __future__ import annotations

import re

from .models import AlignedPair

# Category labels returned by classify().
EMPTY = "empty"
TOC_NUM = "toc_num"
TOC_SECTION = "toc_section"
TINY = "tiny"
BULLET = "bullet"
PROSE = "prose"

_PUNCT_ONLY_RE = re.compile(r"^[\s\-–—.,;:!?'\"()\[\]]+$")  # noqa: RUF001
_SECTION_START_RE = re.compile(r"^\d+(\.\d+){1,}")
_PAGE_NUM_END_RE = re.compile(r"\d{1,4}\s*$")
_SECTION_MARKER_RE = re.compile(r"\d+\.\d+")


def classify(pair: AlignedPair) -> str:
    """Classify an aligned pair into a routing category.

    Args:
        pair: The aligned source/target pair.

    Returns:
        One of ``empty``, ``toc_num``, ``toc_section``, ``tiny``, ``bullet``, ``prose``.
    """
    source = pair.source
    target = pair.target
    source_core = (
        (source.insertion if source else "") + (source.deletion if source else "")
    ).strip()
    target_core = (
        (target.insertion if target else "") + (target.deletion if target else "")
    ).strip()
    combined = f"{source_core} {target_core}".strip()
    total = len(combined)

    if not combined:
        return EMPTY
    if re.fullmatch(r"\d+", source_core) and re.fullmatch(r"\d+", target_core):
        return TOC_NUM
    if re.fullmatch(r"\d{1,4}", source_core) and not target_core:
        return TOC_NUM
    if re.fullmatch(r"[\d.]+", source_core) or re.fullmatch(r"[\d.]+", target_core):
        return TOC_SECTION
    if total < 5:
        return TINY
    if _PUNCT_ONLY_RE.fullmatch(combined):
        return TINY
    if ((source and source.is_list_item) or (target and target.is_list_item)) and total < 60:
        return BULLET
    return PROSE


def looks_like_toc_entry(text: str) -> bool:
    """Return whether accepted text resembles a table-of-contents entry.

    A TOC entry typically starts with a multi-level section number and ends with a
    page number, or concatenates two section markers on one line.
    """
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) > 400:
        return False
    starts_with_section = _SECTION_START_RE.match(stripped) is not None
    ends_with_page_num = _PAGE_NUM_END_RE.search(stripped) is not None
    two_section_markers = len(_SECTION_MARKER_RE.findall(stripped)) >= 2
    return (starts_with_section and ends_with_page_num) or two_section_markers
