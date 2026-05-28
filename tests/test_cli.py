"""Tests for the typer CLI."""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from tc_qa_checker.cli import app
from tests.fixtures import build_docx, ins, paragraph, run

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _write_pair(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source.docx"
    target = tmp_path / "target.docx"
    source.write_bytes(build_docx(paragraph(run("Treat for "), ins("35 cycles"))))
    target.write_bytes(build_docx(paragraph(run("Tratar por "), ins("28 ciclos"))))
    return source, target


def test_cli_text_output(tmp_path: Path) -> None:
    source, target = _write_pair(tmp_path)
    result = runner.invoke(app, ["--source", str(source), "--target", str(target)])
    assert result.exit_code == 0
    assert "Wrong number in target" in result.output


def test_cli_json_output(tmp_path: Path) -> None:
    source, target = _write_pair(tmp_path)
    result = runner.invoke(app, ["--source", str(source), "--target", str(target), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["category"] == "Wrong number in target"


def test_cli_missing_file_errors(tmp_path: Path) -> None:
    target = tmp_path / "target.docx"
    target.write_bytes(build_docx())
    result = runner.invoke(app, ["--source", str(tmp_path / "nope.docx"), "--target", str(target)])
    assert result.exit_code != 0


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # Rich may colorize the help, splitting option names across ANSI codes; strip them first.
    clean = _ANSI_RE.sub("", result.output)
    assert "--source" in clean
