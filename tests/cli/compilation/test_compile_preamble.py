"""Tests for LaTeX compilation preambles."""

from vbagent.cli.compilation.compile_main import generate_preamble
from vbagent.compile import _build_document


def test_generate_preamble_defines_ansint():
    preamble = generate_preamble(subject="physics", title="Problems", include_all=True)

    assert r"\newcommand{\ansint}[1]{\textcolor{red!95}{#1}}" in preamble


def test_build_document_defines_ansint():
    document = _build_document(r"\item Example \ansint{5}", subject="physics")

    assert r"\newcommand{\ansint}[1]{\textcolor{red!95}{#1}}" in document
