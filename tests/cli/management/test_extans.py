from click.testing import CliRunner

from vbagent.cli.management.extans import (
    _add_answer_key_to_main,
    _format_latex,
    extans,
)


def test_format_latex_answer_key_uses_requested_layout():
    output = _format_latex({1: "A", 2: "3"})

    assert "\\begin{center}\n    \\textsc{Answer Key}\n\\end{center}" in output
    assert "\\begin{multicols}{7}" in output
    assert "    \\item (a)" in output
    assert "    \\item (3)" in output
    assert output.endswith("\\end{multicols}")


def test_subjective_answer_key_preserves_latex_and_uses_two_columns():
    answer = r"Stable: $C$; unstable: $A$, $E$; $\Delta U>0$."
    output = _format_latex({1: answer}, {1: "subjective"})

    assert "\\begin{multicols}{2}" in output
    assert f"    \\item {answer}" in output
    assert "stable: $c$" not in output
    assert f"\\item ({answer})" not in output


def test_mixed_answer_key_uses_types_for_each_answer():
    output = _format_latex(
        {1: "B", 2: "5", 3: r"$x=\frac{b}{2a}$, stable."},
        {1: "mcq", 2: "integer", 3: "subjective"},
    )

    assert "\\begin{multicols}{2}" in output
    assert "    \\item (b)" in output
    assert "    \\item (5)" in output
    assert r"    \item $x=\frac{b}{2a}$, stable." in output


def test_extans_cli_extracts_subjective_answer_from_project(tmp_path):
    scans = tmp_path / "agentic" / "scans"
    scans.mkdir(parents=True)
    answer = r"Stable: $C$; unstable: $A$, $E$."
    (scans / "problem_1.tex").write_text(
        "\\item Find equilibrium.\n"
        "\\begin{solution}\nWork.\n\\end{solution}\n"
        f"\\begin{{finalanswer}}\n{answer}\n\\end{{finalanswer}}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.tex"
    main.write_text(
        "\\begin{document}\n"
        "\\input{agentic/scans/problem_1.tex}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    output = tmp_path / "answer_key.tex"

    result = CliRunner().invoke(
        extans,
        ["--file", str(main), "--format", "latex", "--output", str(output)],
        input="n\n",
    )

    assert result.exit_code == 0, result.output
    answer_key = output.read_text(encoding="utf-8")
    assert "\\begin{multicols}{2}" in answer_key
    assert f"\\item {answer}" in answer_key
    assert "Add the answer key" in result.output


def _write_mcq_project(tmp_path):
    scans = tmp_path / "agentic" / "scans"
    scans.mkdir(parents=True)
    (scans / "problem_1.tex").write_text(
        "\\item Example\n"
        "\\begin{tasks}(2)\n"
        "\\task First \\ans\n"
        "\\task Second\n"
        "\\end{tasks}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.tex"
    main.write_text(
        "\\begin{document}\n"
        "\\begin{enumerate}\n"
        "\\input{agentic/scans/problem_1.tex}\n"
        "\\end{enumerate}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    return main


def test_extans_accepts_positional_main_file_and_prompts_to_add(tmp_path):
    main = _write_mcq_project(tmp_path)
    output = tmp_path / "answer_key.tex"

    result = CliRunner().invoke(
        extans,
        [str(main), "--format", "latex", "--output", str(output)],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    content = main.read_text(encoding="utf-8")
    expected = (
        "\\end{enumerate}\n\n"
        "\\vspace*{\\fill}\n"
        "\\input{answer_key.tex}"
    )
    assert expected in content
    assert content.index(r"\input{answer_key.tex}") < content.index(r"\end{document}")


def test_extans_add_implies_latex_output_and_is_idempotent(tmp_path):
    main = _write_mcq_project(tmp_path)

    first = CliRunner().invoke(extans, [str(main), "--add"])
    second = CliRunner().invoke(extans, [str(main), "--add"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert (tmp_path / "answer_key.tex").exists()
    content = main.read_text(encoding="utf-8")
    assert content.count(r"\input{answer_key.tex}") == 1
    assert "already included" in second.output


def test_add_answer_key_does_not_change_main_without_enumerate(tmp_path):
    main = tmp_path / "main.tex"
    original = "\\begin{document}\nNo list.\n\\end{document}\n"
    main.write_text(original, encoding="utf-8")
    answer_key = tmp_path / "answer_key.tex"
    answer_key.write_text("Answer key", encoding="utf-8")

    status = _add_answer_key_to_main(main, answer_key)

    assert status == "missing_enumerate"
    assert main.read_text(encoding="utf-8") == original
