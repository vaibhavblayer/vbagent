"""Regression tests for the tikzphysics v1.2 prompt contract."""

from vbagent.agents.diagram.physics.mechanics import validate_mechanics_output
from vbagent.prompts.content_generation.scanner.physics.common import (
    TIKZ_GUIDELINES,
    TIKZ_GUIDELINES_SHORT,
)
from vbagent.prompts.content_generation.solution.physics.common import (
    PHYSICS_PACKAGES,
)
from vbagent.prompts.diagram.physics import fbd, generic, mechanics, optics, setup
from vbagent.prompts.diagram.tikz_checker import get_review_checklist
from vbagent.prompts.quality.format_checker import SYSTEM_PROMPT as FORMAT_CHECKER_PROMPT
from vbagent.prompts.subjects import get_subject_config


def test_mechanics_prompt_uses_tikzphysics_v12_public_api():
    prompt = mechanics.SYSTEM_PROMPT

    for required in (
        "tikzphysics v1.2.0",
        "physicsblock",
        "physicsspring",
        "physicspulley",
        "physicsground",
        "physicswedge",
        "physicsramp",
        "physicscurvedramp",
        r"\draw[rope]",
        "to[over pulley=P]",
        "tangent-before-T",
        "curve-tangent-before-T",
        "curve-normal-T",
        r"\physicsrampangle",
        "particle",
        "disk",
        "ring",
        "pin-support",
        "roller-support",
        "pendulum",
        r"\physicshelp",
        r"\geometryvalue",
    ):
        assert required in prompt

    for legacy_style in (
        "pulley/.style",
        "block/.style",
        "spring/.style",
    ):
        assert legacy_style not in prompt

    for removed_spring_api in ("coil-start", "coil-mid", "coil-end", "anchor=start", "anchor=end"):
        assert removed_spring_api not in prompt

    assert "physicsspring` is a path decoration" in prompt
    assert r"\physicsstringoverpulley" in prompt  # compatibility guidance remains


def test_problem_setup_and_fbd_prompts_share_package_boundary():
    assert "tikzphysics v1.2.0" in setup.SYSTEM_PROMPT
    assert r"\draw[rope]" in setup.SYSTEM_PROMPT
    assert "to[over pulley=P]" in setup.SYSTEM_PROMPT
    assert "generic `kinematikz` frame" in setup.SYSTEM_PROMPT
    assert "`tikzphysics` v1.2.0" in fbd.SYSTEM_PROMPT
    assert "Usually omit the physical surface" in fbd.SYSTEM_PROMPT
    assert "physicsblock" in fbd.SYSTEM_PROMPT
    assert "`particle` style" in fbd.SYSTEM_PROMPT


def test_optics_prompt_uses_v12_component_shapes_and_surface_anchors():
    prompt = optics.SYSTEM_PROMPT

    for required in (
        "tikzphysics` v1.2.0",
        "physicsconcavemirror",
        "physicsconvexmirror",
        "physicsconvexlens",
        "physicsconcavelens",
        "physicsslab",
        "physicsprism",
        "L.back-65",
        "P.right-65",
    ):
        assert required in prompt

    assert "does not solve Snell's law" in prompt


def test_generic_and_review_prompts_preserve_semantic_mechanics_geometry():
    review = get_review_checklist("physics")

    for prompt in (
        generic.SYSTEM_PROMPT,
        review,
        FORMAT_CHECKER_PROMPT,
        TIKZ_GUIDELINES,
        TIKZ_GUIDELINES_SHORT,
    ):
        assert "tikzphysics v1.2" in prompt
        assert "physicsblock" in prompt

    assert r"\draw[rope]" in generic.SYSTEM_PROMPT
    assert "to[over pulley=P]" in generic.SYSTEM_PROMPT
    assert r"\draw[rope]" in review
    assert r"\draw[rope]" in FORMAT_CHECKER_PROMPT

    for prompt in (generic.SYSTEM_PROMPT, review, FORMAT_CHECKER_PROMPT):
        for removed_spring_api in ("coil-mid", "coil-start", "coil-end", "anchor=start", "anchor=end"):
            assert removed_spring_api not in prompt


def test_physics_subject_and_solution_packages_include_tikzphysics():
    config = get_subject_config("physics")

    assert "tikzphysics" in config.packages
    assert "`tikzphysics` v1.2" in config.package_instructions
    assert r"\usepackage{tikzphysics}" in PHYSICS_PACKAGES


def test_mechanics_validator_accepts_collision_safe_package_shapes():
    code = r"""\begin{tikzpicture}
\node[physicscurvedramp] (R) at (0,0) {};
\node[physicsblock] (B) at (R.curve-50) {$m$};
\end{tikzpicture}"""

    assert validate_mechanics_output(code)
