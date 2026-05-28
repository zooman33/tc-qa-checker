"""Programmatic synthetic DOCX builders for tests.

Everything here is generated in code from invented strings — no real client content,
translation memories, or deliverables are ever used.
"""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _t(text: str) -> str:
    return f'<w:t xml:space="preserve">{escape(text)}</w:t>'


def run(text: str) -> str:
    """A plain run."""
    return f"<w:r>{_t(text)}</w:r>"


def ins(text: str, wid: int = 1) -> str:
    """An inserted run (``<w:ins>``)."""
    return f'<w:ins w:id="{wid}"><w:r>{_t(text)}</w:r></w:ins>'


def dele(text: str, wid: int = 1) -> str:
    """A deleted run (``<w:del>`` with ``<w:delText>``)."""
    return (
        f'<w:del w:id="{wid}"><w:r>'
        f'<w:delText xml:space="preserve">{escape(text)}</w:delText>'
        f"</w:r></w:del>"
    )


def move_from(text: str, wid: int = 1) -> str:
    """A move-from run."""
    return (
        f'<w:moveFrom w:id="{wid}"><w:r>'
        f'<w:delText xml:space="preserve">{escape(text)}</w:delText>'
        f"</w:r></w:moveFrom>"
    )


def move_to(text: str, wid: int = 1) -> str:
    """A move-to run."""
    return f'<w:moveTo w:id="{wid}"><w:r>{_t(text)}</w:r></w:moveTo>'


def paragraph(*content: str, list_item: bool = False, para_mark_inserted: bool = False) -> str:
    """A paragraph wrapping the given run/change fragments."""
    inner = ""
    if para_mark_inserted:
        inner += '<w:rPr><w:ins w:id="900"/></w:rPr>'
    if list_item:
        inner += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
    ppr = f"<w:pPr>{inner}</w:pPr>" if inner else ""
    return f"<w:p>{ppr}{''.join(content)}</w:p>"


def table(*paragraphs: str) -> str:
    """A single-row table; each paragraph becomes its own cell."""
    cells = "".join(f"<w:tc>{p}</w:tc>" for p in paragraphs)
    return f"<w:tbl><w:tr>{cells}</w:tr></w:tbl>"


def build_docx(*body_parts: str) -> bytes:
    """Assemble a minimal DOCX (only ``word/document.xml``) from body fragments."""
    doc = f'<w:document xmlns:w="{W}"><w:body>{"".join(body_parts)}</w:body></w:document>'
    return build_raw(doc)


def build_raw(document_xml: str) -> bytes:
    """Wrap raw ``document.xml`` content in a DOCX zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return buf.getvalue()


def build_non_docx() -> bytes:
    """A zip with no ``word/document.xml`` (to exercise the error path)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("other.txt", "not a word document")
    return buf.getvalue()
