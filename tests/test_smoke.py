"""Smoke test: the package imports and exposes a version string."""

import tc_qa_checker


def test_version_is_exposed() -> None:
    assert tc_qa_checker.__version__
