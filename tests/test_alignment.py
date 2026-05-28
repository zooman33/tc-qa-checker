"""Tests for change-unit and paragraph alignment."""

from __future__ import annotations

from tc_qa_checker.alignment import (
    align_units,
    find_fingerprint_anchors,
    fingerprints_match,
    group_units,
    pair_paragraphs,
    paragraph_fingerprint,
)
from tc_qa_checker.models import ParagraphInfo, TrackChange


def _para(idx: int, accepted: str, *, list_item: bool = False) -> ParagraphInfo:
    return ParagraphInfo(
        idx=idx,
        accepted=accepted,
        raw=accepted,
        is_list_item=list_item,
        paragraph_mark_inserted=False,
        ins_count=0,
        del_count=0,
        is_in_table_cell=False,
    )


def test_group_units_merges_by_paragraph() -> None:
    changes = [
        TrackChange("ins", "abc", 0),
        TrackChange("ins", "def", 0),
        TrackChange("del", "x", 0),
    ]
    paras = [_para(0, "accepted text", list_item=True)]
    units = group_units(changes, paras)
    assert len(units) == 1
    unit = units[0]
    assert unit.insertion == "abcdef"
    assert unit.ins_list == ["abc", "def"]
    assert unit.deletion == "x"
    assert unit.accepted_text == "accepted text"
    assert unit.is_list_item is True


def test_align_units_matches_by_position() -> None:
    src = group_units([TrackChange("ins", "55", 1)], [_para(1, "55")])
    tgt = group_units([TrackChange("ins", "55", 1)], [_para(1, "55")])
    pairs = align_units(src, tgt, 50, 2, 2)
    matched = [p for p in pairs if p.source and p.target]
    assert len(matched) == 1


def test_align_units_handles_empty_target() -> None:
    src = group_units([TrackChange("ins", "x", 0)], [_para(0, "x")])
    pairs = align_units(src, [], 50, 1, 0)
    assert len(pairs) == 1
    assert pairs[0].source is not None
    assert pairs[0].target is None


def test_paragraph_fingerprint_tokens() -> None:
    fp = paragraph_fingerprint("Dose ABC-123 (QOL) 12 weeks on 05JAN2026")
    assert "ABC-123" in fp
    assert "QOL" in fp
    assert "12" in fp
    assert "05JAN2026" in fp


def test_fingerprints_match_requires_shared_tokens() -> None:
    ok, jac = fingerprints_match({"ABC-1", "12"}, {"ABC-1", "12"})
    assert ok is True
    assert jac == 1.0
    ok2, _ = fingerprints_match({"ABC-1"}, {"ABC-1"})
    assert ok2 is False  # below min_size


def test_find_anchors_and_pairing() -> None:
    src = [_para(0, "Dose ABC-123 over 12 weeks here"), _para(1, "no tokens at all here")]
    tgt = [_para(0, "Dosis ABC-123 durante 12 semanas"), _para(1, "sin nada relevante aqui")]
    anchors = find_fingerprint_anchors(src, tgt)
    assert (0, 0) in anchors
    pairing, confidence, _anchors = pair_paragraphs(src, tgt)
    assert pairing[0] == 0
    assert confidence[0] == "HIGH"


def test_pair_paragraphs_empty() -> None:
    pairing, confidence, anchors = pair_paragraphs([], [])
    assert pairing == {}
    assert confidence == {}
    assert anchors == []
