"""End-to-end tests for the analysis engine."""

from __future__ import annotations

from pathlib import Path

from tc_qa_checker import analyze, analyze_files
from tc_qa_checker.models import Severity
from tests.fixtures import build_docx, ins, paragraph, run


def _doc(prefix: str, inserted: str) -> bytes:
    return build_docx(paragraph(run(prefix), ins(inserted)))


def test_analyze_flags_number_mismatch() -> None:
    source = _doc("Treat for ", "35 cycles")
    target = _doc("Tratar por ", "28 ciclos")
    findings = analyze(source, target)
    assert len(findings) == 1
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].category == "Wrong number in target"


def test_analyze_clean_when_numbers_match() -> None:
    source = _doc("Treat for ", "35 cycles")
    target = _doc("Tratar por ", "35 ciclos")
    assert analyze(source, target) == []


def test_analyze_empty_documents() -> None:
    assert analyze(build_docx(), build_docx()) == []


def test_analyze_files_round_trip(tmp_path: Path) -> None:
    source_path = tmp_path / "source.docx"
    target_path = tmp_path / "target.docx"
    source_path.write_bytes(_doc("Dose ", "10 mg"))
    target_path.write_bytes(_doc("Dosis ", "20 mg"))
    findings = analyze_files(source_path, target_path)
    assert any(f.category == "Wrong number in target" for f in findings)


def test_analyze_large_input_is_stable() -> None:
    source = build_docx(*(paragraph(run("Sentence number "), ins(f"{i} items")) for i in range(60)))
    target = build_docx(
        *(paragraph(run("Frase numero "), ins(f"{i} elementos")) for i in range(60))
    )
    # Matching numbers on both sides -> no findings, but the pipeline must complete.
    assert analyze(source, target) == []
