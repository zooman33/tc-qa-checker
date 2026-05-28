"""Numeric detectors.

* :func:`wrong_number_in_target` (CRITICAL) compares inserted numerals block-by-block
  and fires when the target amendment uses a different figure than the source. It is
  gated by the robust paragraph-level pairing to avoid firing across drifted pairs.
* :func:`missing_numbers` (MAJOR, legacy) flags numerals present in the source insert
  but absent from the target insert and accepted text. Suppressed when the wrong-number
  detector already fired on the same paragraph.
"""

from __future__ import annotations

import re

from ..models import AlignedPair, Finding, Severity
from .base import PairContext, make_finding, register

_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")


def extract_numbers(text: str) -> list[str]:
    """Return all integer/decimal numerals in ``text``."""
    if not text:
        return []
    return _NUMBER_RE.findall(text)


def normalize_number(value: str) -> str:
    """Normalize locale/format differences so numerals compare correctly.

    Strips whitespace, treats ``,`` as a decimal point, and drops leading zeros on
    plain integers (keeping a bare ``0``).
    """
    cleaned = value.replace(" ", "").replace(",", ".")
    if re.match(r"^0+\d", cleaned):
        return cleaned.lstrip("0")
    return cleaned


@register("wrong_number_in_target", pre_toc=True)
def wrong_number_in_target(pair: AlignedPair, ctx: PairContext) -> list[Finding]:
    """Fire CRITICAL when a target insert numeral diverges from the source insert."""
    source = pair.source
    target = pair.target
    if source is None or target is None:
        return []

    # Alignment-drift gate: trust the paragraph-level pairing over unit-DP positions.
    conf = ctx.para_confidence.get(source.para_idx, "LOW")
    trusted_target = ctx.para_pairing.get(source.para_idx)
    drift_detected = (
        conf in ("HIGH", "MEDIUM")
        and trusted_target is not None
        and trusted_target != target.para_idx
    )
    if drift_detected:
        return []

    source_blocks = source.ins_list or [source.insertion]
    target_blocks = target.ins_list or [target.insertion]
    target_accepted_nums = {normalize_number(n) for n in extract_numbers(target.accepted_text)}

    for bi, raw_source_block in enumerate(source_blocks):
        source_block = raw_source_block.strip()
        target_block = (
            target_blocks[bi]
            if bi < len(target_blocks)
            else (target_blocks[0] if target_blocks else "")
        ).strip()
        if not source_block or not target_block:
            continue
        source_nums = [normalize_number(n) for n in extract_numbers(source_block)]
        target_nums = [normalize_number(n) for n in extract_numbers(target_block)]
        if not source_nums or not target_nums:
            continue
        source_set = set(source_nums)
        target_set = set(target_nums)
        wrong_in_target = [
            n for n in source_set if n not in target_set and n not in target_accepted_nums
        ]
        if not wrong_in_target:
            continue
        phantom_in_target = [n for n in target_set if n not in source_set]
        if not phantom_in_target:
            continue
        ctx.wrong_number_fired = True
        return [
            make_finding(
                pair,
                severity=Severity.CRITICAL,
                category="Wrong number in target",
                source="mechanical",
                issue=(
                    f"Source INS contains [{', '.join(sorted(source_set))}] but target INS "
                    f"contains [{', '.join(sorted(target_set))}]. Target value diverges from "
                    "source amendment."
                ),
                suggestion=(
                    "Verify the linguist used the source INS value. "
                    f'Source INS block: "{source_block[:100]}". '
                    f'Target INS block: "{target_block[:100]}". '
                    f"Replace the target numeral(s) with the source value(s): "
                    f"{', '.join(wrong_in_target)}."
                ),
            )
        ]
    return []


@register("missing_numbers")
def missing_numbers(pair: AlignedPair, ctx: PairContext) -> list[Finding]:
    """Fire MAJOR when source-insert numerals are missing from the target."""
    if ctx.wrong_number_fired:
        return []
    source = pair.source
    target = pair.target
    if source is None or target is None:
        return []

    source_nums = extract_numbers(source.insertion)
    target_nums = extract_numbers(target.insertion)
    if not source_nums and not target_nums:
        return []

    source_set = {normalize_number(n) for n in source_nums}
    target_set = {normalize_number(n) for n in target_nums}
    accepted_set = {normalize_number(n) for n in extract_numbers(target.accepted_text)}
    real_missing = [n for n in source_set if n not in target_set and n not in accepted_set]
    if not real_missing:
        return []
    return [
        make_finding(
            pair,
            severity=Severity.MAJOR,
            category="Numbers",
            source="mechanical",
            issue=(
                f"Numbers in source insert [{', '.join(sorted(real_missing))}] not found in "
                "target insert or accepted text"
            ),
            suggestion=(
                "Verify the target translation includes these numbers: "
                f"{', '.join(sorted(real_missing))}"
            ),
        )
    ]
