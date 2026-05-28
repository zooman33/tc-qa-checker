"""tc-qa-checker: track-changes verification for bilingual DOCX translation files."""

from __future__ import annotations

from .engine import analyze, analyze_files
from .models import Finding, Severity

__version__ = "0.1.0"

__all__ = ["Finding", "Severity", "__version__", "analyze", "analyze_files"]
