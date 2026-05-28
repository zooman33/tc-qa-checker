"""Extend the engine with a custom detector via the registry.

Detectors are plain ``(pair, context) -> list[Finding]`` callables registered with
``@register``. Anything registered before you call ``analyze`` is included in the sweep.
Here we add a rule that flags an untranslated placeholder ("TODO") left in a target
insertion, then run the full pipeline. Run it with:

    python docs/examples/02_custom_detector.py
"""

from __future__ import annotations

import io
import zipfile

from tc_qa_checker import analyze
from tc_qa_checker.detectors import make_finding, register
from tc_qa_checker.detectors.base import PairContext
from tc_qa_checker.models import AlignedPair, Finding, Severity

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


@register("placeholder_left_in_target", categories=("prose", "bullet"))
def placeholder_left_in_target(pair: AlignedPair, ctx: PairContext) -> list[Finding]:
    """Flag a 'TODO' placeholder left behind in a target insertion."""
    target = pair.target
    if target is not None and "TODO" in target.insertion:
        return [
            make_finding(
                pair,
                severity=Severity.MAJOR,
                category="Placeholder in target",
                source="custom",
                anchor="TODO",
                issue="Target insertion still contains a 'TODO' placeholder.",
                suggestion="Replace the placeholder with the final translation before delivery.",
            )
        ]
    return []


def make_docx(prefix: str, inserted: str) -> bytes:
    """Build a one-paragraph DOCX with a plain run followed by an inserted run."""
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
    source = make_docx("The dose is ", "administered weekly")
    target = make_docx("La dosis es ", "TODO traducir esto")

    findings = analyze(source, target)
    for finding in findings:
        print(f"[{finding.severity}] {finding.category}: {finding.issue}")


if __name__ == "__main__":
    main()
