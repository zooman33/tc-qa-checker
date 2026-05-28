"""Detector registry and shared helpers for the mechanical sweep.

A detector is a callable ``(pair, context) -> list[Finding]``. Detectors register
themselves with :func:`register`, declaring whether they run *before* TOC
suppression and which classification categories they apply to.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..models import AlignedPair, Finding, Severity


@dataclass
class PairContext:
    """Per-pair state shared across detectors during one sweep.

    Attributes:
        para_pairing: Paragraph-level pairing (source idx -> target idx or None).
        para_confidence: Paragraph-level pairing confidence per source idx.
        wrong_number_fired: Set by the wrong-number detector to suppress the legacy
            numbers check on the same paragraph.
    """

    para_pairing: dict[int, int | None]
    para_confidence: dict[int, str]
    wrong_number_fired: bool = False


DetectorFunc = Callable[[AlignedPair, PairContext], list[Finding]]


@dataclass(frozen=True)
class Detector:
    """A registered detector and its scheduling metadata."""

    name: str
    func: DetectorFunc
    pre_toc: bool = False
    categories: tuple[str, ...] | None = None


_REGISTRY: list[Detector] = []


def register(
    name: str, *, pre_toc: bool = False, categories: tuple[str, ...] | None = None
) -> Callable[[DetectorFunc], DetectorFunc]:
    """Register a detector function.

    Args:
        name: Stable detector name.
        pre_toc: If true, the detector runs before TOC suppression.
        categories: Classification categories the detector applies to; ``None`` means
            every non-TOC category.

    Returns:
        A decorator that registers and returns the function unchanged.
    """

    def decorator(func: DetectorFunc) -> DetectorFunc:
        _REGISTRY.append(Detector(name=name, func=func, pre_toc=pre_toc, categories=categories))
        return func

    return decorator


def registry() -> list[Detector]:
    """Return a copy of the registered detectors in registration order."""
    return list(_REGISTRY)


def make_finding(
    pair: AlignedPair,
    *,
    severity: Severity,
    category: str,
    source: str,
    issue: str,
    suggestion: str,
    anchor: str = "",
) -> Finding:
    """Build a :class:`Finding`, copying source/target context from the pair."""
    src = pair.source
    tgt = pair.target
    para_idx = tgt.para_idx if tgt is not None else (src.para_idx if src else -1)
    return Finding(
        para_idx=para_idx,
        severity=severity,
        category=category,
        source=source,
        issue=issue,
        suggestion=suggestion,
        anchor=anchor,
        source_del=src.deletion if src else "",
        source_ins=src.insertion if src else "",
        target_del=tgt.deletion if tgt else "",
        target_ins=tgt.insertion if tgt else "",
        source_accepted=src.accepted_text if src else "",
        target_accepted=tgt.accepted_text if tgt else "",
    )
