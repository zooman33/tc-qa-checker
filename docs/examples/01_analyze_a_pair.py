"""Analyze a source/target DOCX pair and print findings as text and JSON.

This example builds two tiny synthetic DOCX files in memory (so it runs with no input
files) where the target re-applies a source edit with the wrong number. Run it with:

    python docs/examples/01_analyze_a_pair.py
"""

from __future__ import annotations

import io
import zipfile

from tc_qa_checker import Severity, analyze
from tc_qa_checker.report import render_json, render_text

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(prefix: str, inserted: str) -> bytes:
    """Build a one-paragraph DOCX: a plain run followed by an inserted run."""
    paragraph = (
        f"<w:p><w:r><w:t>{prefix}</w:t></w:r>"
        f'<w:ins w:id="1"><w:r><w:t>{inserted}</w:t></w:r></w:ins></w:p>'
    )
    document = f'<w:document xmlns:w="{W}"><w:body>{paragraph}</w:body></w:document>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def main() -> None:
    # The source amends the count to 35; the target mistakenly uses 28.
    source = make_docx("Continue treatment for ", "35 cycles")
    target = make_docx("Continuar el tratamiento durante ", "28 ciclos")

    findings = analyze(source, target)

    print("=== Text report ===")
    print(render_text(findings))

    print("\n=== JSON report ===")
    print(render_json(findings))

    critical = [f for f in findings if f.severity is Severity.CRITICAL]
    print(f"\n{len(critical)} critical finding(s).")


if __name__ == "__main__":
    main()
