"""Tests for DOCX track-change extraction."""

from __future__ import annotations

import pytest

from tc_qa_checker.ooxml import extract_track_changes
from tests.fixtures import (
    build_docx,
    build_non_docx,
    build_raw,
    dele,
    ins,
    move_from,
    move_to,
    paragraph,
    run,
    table,
)


def test_accepted_excludes_deletions_and_keeps_insertions() -> None:
    data = build_docx(paragraph(run("Keep "), dele("gone "), ins("added")))
    extraction = extract_track_changes(data)
    assert len(extraction.paragraphs) == 1
    para = extraction.paragraphs[0]
    assert para.accepted == "Keep added"
    assert "gone" in para.raw
    assert "added" in para.raw


def test_changes_are_collected_with_types() -> None:
    data = build_docx(paragraph(run("x"), ins("new"), dele("old")))
    extraction = extract_track_changes(data)
    types = {c.change_type for c in extraction.changes}
    assert types == {"ins", "del"}
    assert any(c.text == "new" for c in extraction.changes)
    assert any(c.text == "old" for c in extraction.changes)


def test_move_from_and_move_to() -> None:
    data = build_docx(paragraph(move_from("here"), move_to("there")))
    extraction = extract_track_changes(data)
    types = {c.change_type for c in extraction.changes}
    assert types == {"moveFrom", "moveTo"}


def test_ins_del_counts_exclude_paragraph_mark() -> None:
    data = build_docx(paragraph(ins("a"), ins("b"), dele("c"), para_mark_inserted=True))
    para = extract_track_changes(data).paragraphs[0]
    assert para.ins_count == 2
    assert para.del_count == 1
    assert para.paragraph_mark_inserted is True


def test_list_item_flag() -> None:
    data = build_docx(paragraph(run("item"), list_item=True))
    assert extract_track_changes(data).paragraphs[0].is_list_item is True


def test_table_cell_flag() -> None:
    data = build_docx(table(paragraph(run("in cell"))), paragraph(run("outside")))
    paras = extract_track_changes(data).paragraphs
    assert paras[0].is_in_table_cell is True
    assert paras[1].is_in_table_cell is False


def test_not_a_docx_raises() -> None:
    with pytest.raises(ValueError, match="Not a Word document"):
        extract_track_changes(build_non_docx())


def test_malformed_xml_raises() -> None:
    with pytest.raises(ValueError, match="parse error"):
        extract_track_changes(build_raw("<w:document><unclosed></w:document>"))


def test_empty_document() -> None:
    data = build_docx()
    extraction = extract_track_changes(data)
    assert extraction.paragraphs == []
    assert extraction.changes == []
