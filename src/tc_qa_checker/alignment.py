"""Paragraph and change-unit alignment between a source and target document.

Two complementary alignments are produced:

* :func:`align_units` aligns *change units* (paragraphs that carry tracked changes)
  with a Needleman-Wunsch DP over positional + length cost. Its output drives the
  per-pair mechanical sweeps.
* :func:`pair_paragraphs` aligns *all* paragraphs using content fingerprints
  (numbers, codes, acronyms, dates). It is more robust to translation drift and is
  used as a cross-check that gates the wrong-number detector.
"""

from __future__ import annotations

import re

from .models import AlignedPair, ChangeUnit, ParagraphInfo, TrackChange

DEFAULT_SKIP_COST = 50

# Fingerprint token patterns (see paragraph_fingerprint).
_BARE_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_NUMERIC_TOKEN_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*(?:days?|weeks?|months?|years?|hours?|minutes?|mg|kg|g|mL|L|"
    r"µg|μg|%|°C|°F|hr|wk|mo|yr|d|h|min)\b)?",
    re.IGNORECASE,
)
_DNT_TOKEN_RE = re.compile(r"\b[A-Z][A-Z0-9-]{1,}\b")
_ACRONYM_TOKEN_RE = re.compile(r"\(([A-Z]{2,})\)")
_DATE_TOKEN_RE = re.compile(r"\d{1,2}[A-Z]{3}\d{2,4}")


def group_units(changes: list[TrackChange], paragraphs: list[ParagraphInfo]) -> list[ChangeUnit]:
    """Group tracked changes by paragraph into :class:`ChangeUnit` records.

    Args:
        changes: Tracked changes for one document, in document order.
        paragraphs: That document's paragraphs (for accepted/raw/list-item context).

    Returns:
        Change units sorted by paragraph index.
    """
    by_para: dict[int, ChangeUnit] = {}
    for change in changes:
        unit = by_para.get(change.para_idx)
        if unit is None:
            unit = ChangeUnit(para_idx=change.para_idx)
            by_para[change.para_idx] = unit
        if change.change_type == "del":
            unit.deletion += change.text
            unit.del_list.append(change.text)
        elif change.change_type == "ins":
            unit.insertion += change.text
            unit.ins_list.append(change.text)
        elif change.change_type == "moveFrom":
            unit.move_from += change.text
        elif change.change_type == "moveTo":
            unit.move_to += change.text

    for unit in by_para.values():
        info = paragraphs[unit.para_idx] if 0 <= unit.para_idx < len(paragraphs) else None
        unit.accepted_text = info.accepted if info else ""
        unit.raw_text = info.raw if info else ""
        unit.is_list_item = info.is_list_item if info else False

    return sorted(by_para.values(), key=lambda u: u.para_idx)


def _unit_match_cost(a: ChangeUnit, b: ChangeUnit, den_a: int, den_b: int) -> float:
    """Positional + length cost of matching two change units."""
    pos_a = a.para_idx / den_a
    pos_b = b.para_idx / den_b
    pos_diff = abs(pos_a - pos_b) * 200
    if re.fullmatch(r"\d+(\.\d+)?", a.insertion.strip()) and re.fullmatch(
        r"\d+(\.\d+)?", b.insertion.strip()
    ):
        return pos_diff * 0.5
    len_ins_diff = abs(len(a.insertion) - len(b.insertion))
    len_del_diff = abs(len(a.deletion) - len(b.deletion))
    return pos_diff + min(len_ins_diff, 80) * 0.4 + min(len_del_diff, 80) * 0.4


def align_units(
    source_units: list[ChangeUnit],
    target_units: list[ChangeUnit],
    skip_cost: int = DEFAULT_SKIP_COST,
    source_para_count: int = 0,
    target_para_count: int = 0,
) -> list[AlignedPair]:
    """Align change units with Needleman-Wunsch.

    Positions are normalized by each document's paragraph count so that asymmetric
    change distributions do not skew the match toward the wrong end of the document.

    Args:
        source_units: Source change units (sorted by paragraph index).
        target_units: Target change units (sorted by paragraph index).
        skip_cost: Cost of leaving a unit unmatched.
        source_para_count: Total source paragraph count (normalization denominator).
        target_para_count: Total target paragraph count.

    Returns:
        Aligned pairs in document order; either side may be ``None``.
    """
    n, m = len(source_units), len(target_units)
    if n == 0 or m == 0:
        unmatched = [AlignedPair(source=u, target=None) for u in source_units]
        unmatched += [AlignedPair(source=None, target=u) for u in target_units]
        return unmatched

    den_a = source_para_count if source_para_count > 0 else (source_units[-1].para_idx or 1)
    den_b = target_para_count if target_para_count > 0 else (target_units[-1].para_idx or 1)

    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i * skip_cost
    for j in range(1, m + 1):
        dp[0][j] = j * skip_cost

    for i in range(1, n + 1):
        a = source_units[i - 1]
        for j in range(1, m + 1):
            mc = dp[i - 1][j - 1] + _unit_match_cost(a, target_units[j - 1], den_a, den_b)
            skip_e = dp[i - 1][j] + skip_cost
            skip_s = dp[i][j - 1] + skip_cost
            if mc <= skip_e and mc <= skip_s:
                dp[i][j] = mc
                bt[i][j] = 1
            elif skip_e <= skip_s:
                dp[i][j] = skip_e
                bt[i][j] = 2
            else:
                dp[i][j] = skip_s
                bt[i][j] = 3

    pairs: list[AlignedPair] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and bt[i][j] == 1:
            pairs.append(AlignedPair(source=source_units[i - 1], target=target_units[j - 1]))
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or bt[i][j] == 2):
            pairs.append(AlignedPair(source=source_units[i - 1], target=None))
            i -= 1
        else:
            pairs.append(AlignedPair(source=None, target=target_units[j - 1]))
            j -= 1
    pairs.reverse()
    return pairs


def paragraph_fingerprint(text: str) -> set[str]:
    """Extract distinctive tokens (numbers, codes, acronyms, dates) from a paragraph."""
    if not text:
        return set()
    tokens: set[str] = set()
    tokens.update(m.group(0) for m in _BARE_NUMBER_RE.finditer(text))
    tokens.update(m.group(0).strip().upper() for m in _NUMERIC_TOKEN_RE.finditer(text))
    tokens.update(m.group(0) for m in _DNT_TOKEN_RE.finditer(text))
    tokens.update(m.group(1) for m in _ACRONYM_TOKEN_RE.finditer(text))
    tokens.update(m.group(0) for m in _DATE_TOKEN_RE.finditer(text))
    return tokens


def fingerprints_match(
    source_fp: set[str], target_fp: set[str], jaccard_min: float = 0.75, min_size: int = 2
) -> tuple[bool, float]:
    """Return ``(ok, jaccard)`` for two fingerprints sharing at least ``min_size`` tokens."""
    if len(source_fp) < min_size or len(target_fp) < min_size:
        return False, 0.0
    intersect = len(source_fp & target_fp)
    if intersect < min_size:
        return False, 0.0
    union = len(source_fp) + len(target_fp) - intersect
    if union == 0:
        return False, 0.0
    jac = intersect / union
    return jac >= jaccard_min, jac


def _token_count(text: str) -> int:
    """Whitespace-delimited token count."""
    return len(re.findall(r"\S+", text)) if text else 0


def _length_compatible(source_text: str, target_text: str) -> bool:
    """Return whether two paragraphs have a compatible token-count ratio (>= 0.4)."""
    a = _token_count(source_text)
    b = _token_count(target_text)
    if a == 0 or b == 0:
        return False
    return min(a, b) / max(a, b) >= 0.4


def find_fingerprint_anchors(
    source_paras: list[ParagraphInfo], target_paras: list[ParagraphInfo]
) -> list[tuple[int, int]]:
    """Find high-confidence ``(source_idx, target_idx)`` anchors via mutual-best fingerprints.

    Mutual-best matches are filtered to a longest increasing subsequence in target index
    so the anchors stay monotonic.
    """
    source_fps = [paragraph_fingerprint(p.accepted) for p in source_paras]
    target_fps = [paragraph_fingerprint(p.accepted) for p in target_paras]

    source_best: dict[int, tuple[int, float]] = {}
    for i, sp in enumerate(source_paras):
        if len(source_fps[i]) < 2:
            continue
        best: tuple[int, float] | None = None
        for j, tp in enumerate(target_paras):
            if len(target_fps[j]) < 2:
                continue
            ok, jac = fingerprints_match(source_fps[i], target_fps[j])
            if not ok or not _length_compatible(sp.accepted, tp.accepted):
                continue
            if best is None or jac > best[1] or (jac == best[1] and abs(j - i) < abs(best[0] - i)):
                best = (tp.idx, jac)
        if best is not None:
            source_best[sp.idx] = best

    target_best: dict[int, tuple[int, float]] = {}
    for j, tp in enumerate(target_paras):
        if len(target_fps[j]) < 2:
            continue
        best = None
        for i, sp in enumerate(source_paras):
            if len(source_fps[i]) < 2:
                continue
            ok, jac = fingerprints_match(source_fps[i], target_fps[j])
            if not ok or not _length_compatible(sp.accepted, tp.accepted):
                continue
            if best is None or jac > best[1] or (jac == best[1] and abs(i - j) < abs(best[0] - j)):
                best = (sp.idx, jac)
        if best is not None:
            target_best[tp.idx] = best

    mutual: list[tuple[int, int, float]] = []
    for source_idx, (target_idx, jac) in source_best.items():
        reverse = target_best.get(target_idx)
        if reverse is not None and reverse[0] == source_idx:
            mutual.append((source_idx, target_idx, jac))
    mutual.sort(key=lambda t: t[0])
    if not mutual:
        return []

    # Longest increasing subsequence over target index.
    length = [1] * len(mutual)
    prev = [-1] * len(mutual)
    for i in range(1, len(mutual)):
        for k in range(i):
            if mutual[k][1] < mutual[i][1] and length[k] + 1 > length[i]:
                length[i] = length[k] + 1
                prev[i] = k
    best_end = max(range(len(mutual)), key=lambda i: length[i])
    result: list[tuple[int, int]] = []
    cur = best_end
    while cur != -1:
        result.append((mutual[cur][0], mutual[cur][1]))
        cur = prev[cur]
    result.reverse()
    return result


def _pair_segment_dp(
    source_seg: list[ParagraphInfo],
    target_seg: list[ParagraphInfo],
    pairing: dict[int, int | None],
    confidence: dict[int, str],
) -> None:
    """Align a segment between anchors and write pairings/confidence in place."""
    n, m = len(source_seg), len(target_seg)
    if n == 0:
        return
    if m == 0:
        for sp in source_seg:
            pairing[sp.idx] = None
            confidence[sp.idx] = "LOW"
        return

    skip = 100
    threshold = 90

    def cost(a: ParagraphInfo, b: ParagraphInfo, ai: int, bi: int) -> float:
        pmi_pen = 60 if a.paragraph_mark_inserted != b.paragraph_mark_inserted else 0
        a_tok = _token_count(a.accepted)
        b_tok = _token_count(b.accepted)
        if a_tok == 0 and b_tok == 0:
            len_pen = 0.0
        elif a_tok == 0 or b_tok == 0:
            len_pen = 80.0
        else:
            ratio = min(a_tok, b_tok) / max(a_tok, b_tok)
            len_pen = 80.0 if ratio < 0.4 else (1 - ratio) * 50
        a_rel = ai / (n - 1) if n > 1 else 0
        b_rel = bi / (m - 1) if m > 1 else 0
        pos_pen = abs(a_rel - b_rel) * 80
        return pmi_pen + len_pen + pos_pen

    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i * skip
        bt[i][0] = 2
    for j in range(1, m + 1):
        dp[0][j] = j * skip
        bt[0][j] = 3
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            mc = dp[i - 1][j - 1] + cost(source_seg[i - 1], target_seg[j - 1], i - 1, j - 1)
            skip_e = dp[i - 1][j] + skip
            skip_s = dp[i][j - 1] + skip
            if mc <= skip_e and mc <= skip_s:
                dp[i][j] = mc
                bt[i][j] = 1
            elif skip_e <= skip_s:
                dp[i][j] = skip_e
                bt[i][j] = 2
            else:
                dp[i][j] = skip_s
                bt[i][j] = 3

    i, j = n, m
    while i > 0 or j > 0:
        b = bt[i][j]
        if b == 1:
            step = cost(source_seg[i - 1], target_seg[j - 1], i - 1, j - 1)
            if step <= threshold:
                pairing[source_seg[i - 1].idx] = target_seg[j - 1].idx
                confidence[source_seg[i - 1].idx] = "MEDIUM"
            else:
                pairing[source_seg[i - 1].idx] = None
                confidence[source_seg[i - 1].idx] = "LOW"
            i -= 1
            j -= 1
        elif b == 2:
            pairing[source_seg[i - 1].idx] = None
            confidence[source_seg[i - 1].idx] = "LOW"
            i -= 1
        else:
            j -= 1


def pair_paragraphs(
    source_paras: list[ParagraphInfo], target_paras: list[ParagraphInfo]
) -> tuple[dict[int, int | None], dict[int, str], list[tuple[int, int]]]:
    """Align all paragraphs via fingerprint anchors plus constrained per-segment DP.

    Args:
        source_paras: Source paragraphs in document order.
        target_paras: Target paragraphs in document order.

    Returns:
        A tuple ``(pairing, confidence, anchors)`` where ``pairing`` maps a source
        paragraph index to a target index (or ``None``), ``confidence`` maps it to
        ``"HIGH"``/``"MEDIUM"``/``"LOW"``, and ``anchors`` are the high-confidence pairs.
    """
    pairing: dict[int, int | None] = {}
    confidence: dict[int, str] = {}
    if not source_paras or not target_paras:
        return pairing, confidence, []

    anchors = find_fingerprint_anchors(source_paras, target_paras)
    edges = [(-1, -1), *anchors, (len(source_paras), len(target_paras))]
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1]
        if i > 0:
            pairing[a[0]] = a[1]
            confidence[a[0]] = "HIGH"
        source_seg = source_paras[a[0] + 1 : b[0]]
        target_seg = target_paras[a[1] + 1 : b[1]]
        _pair_segment_dp(source_seg, target_seg, pairing, confidence)

    return pairing, confidence, anchors
