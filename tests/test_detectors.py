"""Tests for the mechanical detectors and the sweep pipeline."""

from __future__ import annotations

from tc_qa_checker.detectors import dedupe_and_sort, run_mechanical_sweeps
from tc_qa_checker.detectors.base import PairContext
from tc_qa_checker.detectors.boundary import cross_run_boundary
from tc_qa_checker.detectors.completeness import completeness
from tc_qa_checker.detectors.numbers import (
    extract_numbers,
    missing_numbers,
    normalize_number,
    wrong_number_in_target,
)
from tc_qa_checker.models import AlignedPair, ChangeUnit, Finding, Severity


def _pair(
    *,
    source_ins: str = "",
    target_ins: str = "",
    target_accepted: str = "",
    target_del: str = "",
    category: str = "prose",
    source_para: int = 0,
    target_para: int = 0,
) -> AlignedPair:
    source = ChangeUnit(
        para_idx=source_para,
        insertion=source_ins,
        ins_list=[source_ins] if source_ins else [],
    )
    target = ChangeUnit(
        para_idx=target_para,
        insertion=target_ins,
        deletion=target_del,
        accepted_text=target_accepted,
        ins_list=[target_ins] if target_ins else [],
    )
    return AlignedPair(source=source, target=target, category=category)


def _ctx() -> PairContext:
    return PairContext(para_pairing={}, para_confidence={})


def test_extract_numbers_and_normalize() -> None:
    assert extract_numbers("take 5 mg and 12.5 units") == ["5", "12.5"]
    assert normalize_number("1,5") == "1.5"
    assert normalize_number("08") == "8"
    assert normalize_number("0") == "0"


def test_wrong_number_fires_critical() -> None:
    pair = _pair(source_ins="35 cycles", target_ins="28 ciclos", target_accepted="por 28 ciclos")
    ctx = _ctx()
    findings = wrong_number_in_target(pair, ctx)
    assert len(findings) == 1
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].category == "Wrong number in target"
    assert ctx.wrong_number_fired is True


def test_wrong_number_suppressed_by_drift_gate() -> None:
    pair = _pair(
        source_ins="35", target_ins="28", target_accepted="28", source_para=0, target_para=3
    )
    ctx = PairContext(para_pairing={0: 5}, para_confidence={0: "HIGH"})
    assert wrong_number_in_target(pair, ctx) == []


def test_missing_numbers_fires_major() -> None:
    pair = _pair(source_ins="add 5 mg", target_ins="agregar mg", target_accepted="agregar mg")
    findings = missing_numbers(pair, _ctx())
    assert len(findings) == 1
    assert findings[0].severity is Severity.MAJOR
    assert findings[0].category == "Numbers"


def test_missing_numbers_suppressed_when_wrong_number_fired() -> None:
    pair = _pair(source_ins="5", target_ins="x", target_accepted="x")
    ctx = _ctx()
    ctx.wrong_number_fired = True
    assert missing_numbers(pair, ctx) == []


def test_cross_run_boundary_doubled_word() -> None:
    pair = _pair(target_accepted="this is the the result")
    findings = cross_run_boundary(pair, _ctx())
    assert any(
        f.category == "Cross-run boundary" and f.severity is Severity.MAJOR for f in findings
    )


def test_cross_run_boundary_ignores_stopword_repeat() -> None:
    pair = _pair(target_accepted="si si claro")
    findings = cross_run_boundary(pair, _ctx())
    assert all("Doubled word" not in f.issue for f in findings)


def test_cross_run_boundary_double_space_and_merge() -> None:
    double_space = cross_run_boundary(_pair(target_accepted="a  b"), _ctx())
    assert any(f.severity is Severity.MINOR for f in double_space)
    merge = cross_run_boundary(_pair(target_accepted="fin.Inicio"), _ctx())
    assert any("Missing space" in f.issue for f in merge)


def test_completeness_fires_on_untranslated_insertion() -> None:
    pair = _pair(source_ins="A long inserted clause that was never translated", target_ins="")
    findings = completeness(pair, _ctx())
    assert len(findings) == 1
    assert findings[0].severity is Severity.CRITICAL


def test_dedupe_and_sort_orders_by_para_then_severity() -> None:
    findings = [
        Finding(
            para_idx=2, severity=Severity.MINOR, category="X", source="m", issue="i", suggestion="s"
        ),
        Finding(
            para_idx=1, severity=Severity.MAJOR, category="Y", source="m", issue="i", suggestion="s"
        ),
        Finding(
            para_idx=1,
            severity=Severity.CRITICAL,
            category="Z",
            source="m",
            issue="i",
            suggestion="s",
        ),
        # Exact duplicate of the first — should be dropped.
        Finding(
            para_idx=2, severity=Severity.MINOR, category="X", source="m", issue="i", suggestion="s"
        ),
    ]
    result = dedupe_and_sort(findings)
    assert len(result) == 3
    assert [f.para_idx for f in result] == [1, 1, 2]
    assert result[0].severity is Severity.CRITICAL


def test_run_sweeps_suppresses_toc_but_finds_prose() -> None:
    # toc_num routes around the post-TOC detectors: missing_numbers would otherwise
    # flag the dropped "5", but TOC suppression silences it.
    toc_pair = _pair(source_ins="5", target_ins="", target_accepted="", category="toc_num")
    prose_pair = _pair(
        source_ins="35 cycles",
        target_ins="28 ciclos",
        target_accepted="por 28 ciclos",
        category="prose",
        source_para=1,
        target_para=1,
    )
    findings = run_mechanical_sweeps([toc_pair, prose_pair], {}, {})
    categories = {f.category for f in findings}
    assert "Wrong number in target" in categories
    assert all(f.para_idx == 1 for f in findings)
