"""Display-fraction policy must cover previews and every owned document builder."""

import shutil
from pathlib import Path

import pytest

from vbagent.cli.compilation.compile_main import generate_preamble
from vbagent.compile import _build_document, compile_latex
from vbagent.utils.latex import DISPLAY_FRACTION_PREAMBLE


@pytest.mark.parametrize("subject", ("physics", "chemistry", "mathematics", "biology"))
def test_preview_and_main_preambles_use_the_same_fraction_policy(subject):
    for preamble in (_build_document("Test", subject), generate_preamble(subject)):
        assert DISPLAY_FRACTION_PREAMBLE in preamble
        assert preamble.index("amsmath") < preamble.index(DISPLAY_FRACTION_PREAMBLE)


def test_notes_and_revision_documents_use_the_same_policy(tmp_path):
    from vbagent.agents.notes.models import DocumentPlan, SectionContent
    from vbagent.agents.notes.stitcher import stitch_notes
    from vbagent.analysis.brief_generator import _preamble
    from vbagent.analysis.generator import _generate_preamble

    plan = DocumentPlan(title="Fractions", sections=[])
    path = stitch_notes(
        plan,
        [SectionContent(section_title="Test", latex=r"$\frac{1}{2}$")],
        tmp_path / "notes.tex",
    )
    for source in (Path(path).read_text(), _generate_preamble(), _preamble()):
        assert DISPLAY_FRACTION_PREAMBLE in source


def test_default_export_applies_policy_and_preserves_custom_templates(tmp_path):
    from vbagent.export.exporter import Exporter, ExportMode

    source = tmp_path / "question.tex"
    source.write_text(r"$\frac{1}{2}$")
    default = Exporter().export([source], tmp_path / "default", ExportMode.PROJECT)
    assert DISPLAY_FRACTION_PREAMBLE in default.main_tex.read_text()
    custom = Exporter().export(
        [source],
        tmp_path / "custom",
        ExportMode.PROJECT,
        template="Custom {title}\n{content}",
        title="Title",
    )
    assert custom.main_tex.read_text() == "Custom Title\n\\input{question_001}"
    assert (tmp_path / "default" / "question_001.tex").read_text() == source.read_text()


def test_dpp_preamble_uses_policy(tmp_path):
    from vbagent.dpp.builder import DPPBuilder

    output = tmp_path / "dpp.tex"
    # Building a document does not need to query or mutate the question store.
    DPPBuilder.__new__(DPPBuilder)._generate_main_tex([], output, "Fractions")
    assert DISPLAY_FRACTION_PREAMBLE in output.read_text()


@pytest.mark.skipif(
    shutil.which("pdflatex") is None, reason="pdflatex is not installed"
)
def test_fraction_aliases_compile_and_have_identical_dimensions(tmp_path):
    # Matching width, height, and depth catches text-style fractions in inline
    # math and scripts, as well as accidental alias recursion in nested uses.
    comparisons = (
        (r"\frac{1}{2}", r"\dfrac{1}{2}"),
        (r"\tfrac{1}{2}", r"\dfrac{1}{2}"),
        (r"a_{\frac{1}{2}}", r"a_{\dfrac{1}{2}}"),
        (r"a^{\tfrac{1}{2}}", r"a^{\dfrac{1}{2}}"),
        (r"\frac{1}{\tfrac{2}{3}}", r"\dfrac{1}{\dfrac{2}{3}}"),
        (r"\tfrac12", r"\dfrac{1}{2}"),
    )
    lines = []
    for legacy, canonical in comparisons:
        lines.extend(
            (rf"\setbox0=\hbox{{${legacy}$}}", rf"\setbox2=\hbox{{${canonical}$}}")
        )
        for dimension in ("wd", "ht", "dp"):
            lines.append(
                rf"\ifdim\{dimension}0=\{dimension}2\else\errmessage{{Fraction {dimension} mismatch}}\fi"
            )
    lines.append(r"Fractions: $\frac{1}{2},\tfrac{1}{2},\dfrac{1}{2},\binom{3}{2}$.")
    result = compile_latex(
        "\n".join(lines), subject="mathematics", output_dir=str(tmp_path)
    )
    assert result.success, result.error_summary
