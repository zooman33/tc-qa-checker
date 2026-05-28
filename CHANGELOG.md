# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- DOCX (OOXML) track-change extraction: insertions, deletions, moves, accepted text,
  and list / table-cell / inserted-paragraph-mark flags (standard library only).
- Translation-aware alignment: Needleman-Wunsch over change units, plus content-fingerprint
  anchoring (numbers, codes, acronyms, dates) with constrained per-segment DP.
- Deterministic detector pipeline behind a registry — wrong-number-in-target (CRITICAL,
  alignment-drift gated), missing-numbers (MAJOR), untranslated-insertion completeness
  (CRITICAL), and cross-run boundary artifacts (doubled words, double spaces, sentence
  merges). Table-of-contents entries are suppressed.
- `analyze` / `analyze_files` library API and a `tc-qa-checker` Typer CLI with text and
  JSON output.
- Test suite with programmatic synthetic DOCX fixtures (90%+ coverage) and CI
  (ruff, mypy strict, pytest) on Python 3.11.
- Project scaffolding: `src/` layout, tooling config, pre-commit hooks, and contributor docs.
