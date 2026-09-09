"""Tests for LaTeX compilation preambles and diagram assembly."""

from vbagent.cli.compilation.compile_main import generate_main_tex, generate_preamble
from vbagent.compile import _build_document, _parse_errors


def test_generate_preamble_defines_ansint():
    preamble = generate_preamble(subject="physics", title="Problems", include_all=True)

    assert r"\newcommand{\ansint}[1]{\textcolor{red!95}{#1}}" in preamble
    assert r"\DeclareMathOperator{\cosec}{cosec}" in preamble
    assert r"\usepackage{comment, multicol}" in preamble
    assert r"\usepackage{multirow}" in preamble
    assert r"\usepackage{tikzphysics}" in preamble
    assert r"\usepgfplotslibrary{groupplots}" in preamble
    assert r"\geometry{a4paper, margin=0.65in}" in preamble
    assert r"\renewcommand{\ans}{}" in preamble
    assert r"% \excludecomment{solution}" in preamble
    assert r"% \excludecomment{alternatesolution}" in preamble
    for environment in ("hint", "idea", "remark", "finalanswer"):
        assert rf"\excludecomment{{{environment}}}" in preamble


def test_build_document_defines_ansint():
    document = _build_document(r"\item Example \ansint{5}", subject="physics")

    assert r"\newcommand{\ansint}[1]{\textcolor{red!95}{#1}}" in document
    assert r"\DeclareMathOperator{\cosec}{cosec}" in document
    assert r"\usepackage{comment, multicol}" in document
    assert r"\usepackage{multirow}" in document
    assert r"\usepackage{tikzphysics}" in document
    assert r"\usepgfplotslibrary{groupplots}" in document
    assert r"\renewcommand{\ans}{}" in document
    assert r"% \excludecomment{solution}" in document
    assert r"% \excludecomment{alternatesolution}" in document
    for environment in ("hint", "idea", "remark", "finalanswer"):
        assert rf"\excludecomment{{{environment}}}" in document


def test_build_document_sanitizes_structural_blank_lines():
    snippet = r"""\item

\begin{align*}
x &= 1 \\

y &= 2
\end{align*}"""

    document = _build_document(snippet, subject="mathematics")
    align_body = document.split(r"\begin{align*}", 1)[1].split(
        r"\end{align*}", 1
    )[0]

    assert "\\item\n\\begin{align*}" in document
    assert "\n\n" not in align_body


def test_parse_errors_includes_nearby_generated_source():
    source = "\n".join(f"source line {number}" for number in range(1, 21))
    log = """! Package pgfplots Error: unknown plot command.
See the pgfplots documentation.
l.12 \\node
"""

    summary = _parse_errors(log, source)

    assert "Generated source context around line 12" in summary
    assert "source line 5" in summary
    assert ">   12 | source line 12" in summary


def test_generate_main_tex_assembles_matching_problem_tikz(tmp_path):
    scans = tmp_path / "agentic" / "scans"
    tikz = tmp_path / "agentic" / "tikz"
    scans.mkdir(parents=True)
    tikz.mkdir(parents=True)
    (scans / "problem_1.tex").write_text(
        r"\item Example\begin{center}\input{diagram}\end{center}"
    )
    (tikz / "problem_1.tex").write_text(
        r"\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}"
    )

    document = generate_main_tex(
        scans_dir=str(scans),
        output_file=str(tmp_path / "main.tex"),
        title="Problems",
        subject="physics",
    )

    assert r"\input{diagram}" not in document
    assert r"\input{.vbagent_compile/main/problem_1.tex}" in document
    assert "VBAGENT MISSING DIAGRAM" not in document
    staged = tmp_path / ".vbagent_compile" / "main" / "problem_1.tex"
    assert r"\begin{tikzpicture}" in staged.read_text()
    assert r"\input{diagram}" not in staged.read_text()


def test_generate_main_tex_assembles_legacy_assertion_placeholder(tmp_path):
    scans = tmp_path / "agentic" / "scans"
    tikz = tmp_path / "agentic" / "tikz"
    scans.mkdir(parents=True)
    tikz.mkdir(parents=True)
    (scans / "problem_68.tex").write_text(
        r"""\item Figure shows a sequence of photographs.
\begin{center}
    \text{[Diagram]}
\end{center}
\textbf{Statement-1:} Acceleration appears upward."""
    )
    (tikz / "problem_68.tex").write_text(
        r"\begin{tikzpicture}\draw (0,0) circle (0.1);\end{tikzpicture}"
    )

    document = generate_main_tex(
        scans_dir=str(scans),
        output_file=str(tmp_path / "main.tex"),
        title="Problems",
        subject="physics",
    )

    assert "VBAGENT MISSING DIAGRAM" not in document
    staged = tmp_path / ".vbagent_compile" / "main" / "problem_68.tex"
    staged_content = staged.read_text()
    assert "[Diagram]" not in staged_content
    assert staged_content.count(r"\begin{tikzpicture}") == 1
    assert r"\textbf{Statement-1:}" in staged_content


def test_generate_main_tex_uses_compilable_fallback_for_missing_tikz(tmp_path):
    scans = tmp_path / "agentic" / "scans"
    scans.mkdir(parents=True)
    (scans / "problem_10.tex").write_text(r"\item Example \input{diagram}")

    document = generate_main_tex(
        scans_dir=str(scans),
        output_file=str(tmp_path / "main.tex"),
        title="Problems",
        subject="physics",
    )

    assert r"\input{diagram}" not in document
    assert r"\input{.vbagent_compile/main/problem_10.tex}" in document
    assert "% VBAGENT MISSING DIAGRAM: problem_10" in document
    staged = tmp_path / ".vbagent_compile" / "main" / "problem_10.tex"
    assert "[DIAGRAM NOT AVAILABLE: problem_10]" in staged.read_text()
