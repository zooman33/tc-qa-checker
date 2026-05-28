"""DOCX (OOXML) parsing: extract tracked changes and accepted text from ``document.xml``.

Uses the standard library only (``zipfile`` + ``xml.etree.ElementTree``) so the core
engine carries no third-party parsing dependency.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

from .models import Extraction, ParagraphInfo, TrackChange

#: WordprocessingML main namespace.
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_DOCUMENT_PART = "word/document.xml"


def _w(tag: str) -> str:
    """Return ``tag`` qualified with the WordprocessingML namespace."""
    return f"{{{W_NS}}}{tag}"


def _build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    """Build a child -> parent lookup for the whole tree.

    ``ElementTree`` elements do not carry parent pointers, so ancestry checks
    need an explicit map.
    """
    return {child: parent for parent in root.iter() for child in parent}


def _ancestor_is(
    node: ET.Element,
    parent_map: dict[ET.Element, ET.Element],
    local_names: tuple[str, ...],
) -> bool:
    """Return whether any ancestor of ``node`` is a WordprocessingML element in ``local_names``."""
    wanted = {_w(name) for name in local_names}
    current = parent_map.get(node)
    while current is not None:
        if current.tag in wanted:
            return True
        current = parent_map.get(current)
    return False


def _read_document_xml(data: bytes) -> bytes:
    """Return the raw ``word/document.xml`` bytes from a DOCX byte string."""
    with zipfile.ZipFile(BytesIO(data)) as archive:
        try:
            return archive.read(_DOCUMENT_PART)
        except KeyError as exc:
            raise ValueError("Not a Word document (no word/document.xml)") from exc


def extract_track_changes(data: bytes) -> Extraction:
    """Parse a DOCX file and extract per-paragraph structure and tracked changes.

    Args:
        data: Raw bytes of a ``.docx`` file.

    Returns:
        An :class:`~tc_qa_checker.models.Extraction` with paragraph info and changes
        in document order.

    Raises:
        ValueError: If the archive has no ``word/document.xml`` or it fails to parse.
    """
    xml_bytes = _read_document_xml(data)
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"document.xml parse error: {exc}") from exc

    parent_map = _build_parent_map(root)
    paragraphs: list[ParagraphInfo] = []
    changes: list[TrackChange] = []

    for para_idx, para in enumerate(root.iter(_w("p"))):
        t_nodes = list(para.iter(_w("t")))

        accepted = "".join(
            (t.text or "") for t in t_nodes if not _ancestor_is(t, parent_map, ("del", "moveFrom"))
        )
        raw = "".join((t.text or "") for t in t_nodes)
        raw += "".join((dt.text or "") for dt in para.iter(_w("delText")))

        is_list_item = next(para.iter(_w("numPr")), None) is not None
        paragraph_mark_inserted = _has_paragraph_mark_insertion(para)
        ins_count, del_count = _count_top_level_changes(para, parent_map)
        is_in_table_cell = _is_in_table_cell(para, parent_map)

        paragraphs.append(
            ParagraphInfo(
                idx=para_idx,
                accepted=accepted,
                raw=raw,
                is_list_item=is_list_item,
                paragraph_mark_inserted=paragraph_mark_inserted,
                ins_count=ins_count,
                del_count=del_count,
                is_in_table_cell=is_in_table_cell,
            )
        )

        for change_type in ("ins", "del", "moveFrom", "moveTo"):
            for el in para.iter(_w(change_type)):
                if _ancestor_is(el, parent_map, ("ins", "del", "moveFrom", "moveTo")):
                    continue
                text = _change_text(el, change_type)
                if text:
                    changes.append(
                        TrackChange(change_type=change_type, text=text, para_idx=para_idx)
                    )

    return Extraction(paragraphs=paragraphs, changes=changes)


def _change_text(el: ET.Element, change_type: str) -> str:
    """Collect the text of a tracked-change element."""
    if change_type in ("del", "moveFrom"):
        text = "".join((dt.text or "") for dt in el.iter(_w("delText")))
        text += "".join((t.text or "") for t in el.iter(_w("t")))
        return text
    return "".join((t.text or "") for t in el.iter(_w("t")))


def _has_paragraph_mark_insertion(para: ET.Element) -> bool:
    """Return whether the paragraph mark was inserted (``<w:pPr><w:rPr><w:ins/>``)."""
    for ppr in para.findall(_w("pPr")):
        for rpr in ppr.findall(_w("rPr")):
            if rpr.find(_w("ins")) is not None:
                return True
    return False


def _count_top_level_changes(
    para: ET.Element, parent_map: dict[ET.Element, ET.Element]
) -> tuple[int, int]:
    """Count top-level ``<w:ins>`` and ``<w:del>`` runs, excluding the paragraph mark."""
    ins_count = 0
    del_count = 0
    for change_type in ("ins", "del"):
        for el in para.iter(_w(change_type)):
            if _ancestor_is(el, parent_map, ("ins", "del", "moveFrom", "moveTo")):
                continue
            if change_type == "ins":
                parent = parent_map.get(el)
                if parent is not None and parent.tag == _w("rPr"):
                    continue
                ins_count += 1
            else:
                del_count += 1
    return ins_count, del_count


def _is_in_table_cell(para: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> bool:
    """Return whether the paragraph is nested inside a table cell (``<w:tc>``)."""
    current = parent_map.get(para)
    while current is not None:
        if current.tag == _w("tc"):
            return True
        if current.tag == _w("body"):
            break
        current = parent_map.get(current)
    return False
