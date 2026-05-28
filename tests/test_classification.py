"""Tests for pair classification and the TOC heuristic."""

from __future__ import annotations

from tc_qa_checker.classification import classify, looks_like_toc_entry
from tc_qa_checker.models import AlignedPair, ChangeUnit


def _pair(source_text: str = "", target_text: str = "", *, list_item: bool = False) -> AlignedPair:
    source = ChangeUnit(para_idx=0, insertion=source_text, is_list_item=list_item)
    target = ChangeUnit(para_idx=0, insertion=target_text, is_list_item=list_item)
    return AlignedPair(source=source, target=target)


def test_classify_empty() -> None:
    assert classify(_pair("", "")) == "empty"


def test_classify_toc_num_when_both_pure_digits() -> None:
    assert classify(_pair("12", "12")) == "toc_num"


def test_classify_toc_num_source_only_digits() -> None:
    assert classify(_pair("123", "")) == "toc_num"


def test_classify_toc_section() -> None:
    assert classify(_pair("10.3.4", "10.3.4")) == "toc_section"


def test_classify_tiny() -> None:
    assert classify(_pair("ab", "")) == "tiny"


def test_classify_punctuation_only_is_tiny() -> None:
    assert classify(_pair("--- ...", ", ; :")) == "tiny"


def test_classify_bullet() -> None:
    assert classify(_pair("short item", "elemento", list_item=True)) == "bullet"


def test_classify_prose() -> None:
    long_text = "This is a substantial inserted sentence that should classify as prose."
    assert classify(_pair(long_text, "Una frase larga insertada")) == "prose"


def test_looks_like_toc_entry_section_and_page() -> None:
    assert looks_like_toc_entry("10.3.4 Study procedures 42") is True


def test_looks_like_toc_entry_two_markers() -> None:
    assert looks_like_toc_entry("1.2 Intro 3.4 Methods") is True


def test_looks_like_toc_entry_negative() -> None:
    assert looks_like_toc_entry("Just a normal sentence with no section number.") is False
    assert looks_like_toc_entry("") is False
