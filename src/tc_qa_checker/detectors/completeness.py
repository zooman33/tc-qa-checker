"""Completeness detector: substantial source insertion with no target counterpart."""

from __future__ import annotations

from ..models import AlignedPair, Finding, Severity
from .base import PairContext, make_finding, register

_MIN_SOURCE_INS = 20
_MAX_TARGET_CHANGE = 5


@register("completeness")
def completeness(pair: AlignedPair, ctx: PairContext) -> list[Finding]:
    """Fire CRITICAL when the source inserts substantial text but the target does not."""
    source = pair.source
    target = pair.target
    if source is None or target is None:
        return []
    if (
        len(source.insertion) > _MIN_SOURCE_INS
        and len(target.insertion) < _MAX_TARGET_CHANGE
        and len(target.deletion) < _MAX_TARGET_CHANGE
    ):
        return [
            make_finding(
                pair,
                severity=Severity.CRITICAL,
                category="Completeness",
                source="mechanical",
                issue=(
                    "Source introduces substantial inserted text, but no "
                    "corresponding insertion in target"
                ),
                suggestion=(
                    "Verify that this source insertion was translated: "
                    f'"{source.insertion[:80]}..."'
                ),
            )
        ]
    return []
