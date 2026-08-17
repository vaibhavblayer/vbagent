"""Regression tests for solution-agent alternate recommendations."""

from vbagent.models.solution import SolutionOutput
from vbagent.prompts.content_generation.solution import get_solution_prompt


def test_solution_output_defaults_to_no_alternate_recommendation():
    output = SolutionOutput(solution_latex=r"\begin{solution}x=1\end{solution}")

    assert output.alternate_solution_recommended is False
    assert output.alternate_solution_hint is None
    assert output.final_answer_latex is None


def test_solution_prompts_explain_conditional_alternate_generation():
    for subject in ("physics", "chemistry", "mathematics", "biology"):
        for question_type in ("subjective", "mcq_sc", "mcq_mc", "assertion_reason", "match", "passage"):
            prompt = get_solution_prompt(question_type, subject)
            assert '"alternate_solution_recommended": false' in prompt
            assert '"alternate_solution_hint": null' in prompt

        prompt = get_solution_prompt("subjective", subject)
        assert "Do not write the alternate solution itself" in prompt


def test_subjective_solution_prompts_require_separate_final_answer():
    for subject in ("physics", "chemistry", "mathematics", "biology"):
        prompt = get_solution_prompt("subjective", subject)

        assert "Subjective Final Answer Field (REQUIRED)" in prompt
        assert "`final_answer_latex`" in prompt
        assert "answer-key-ready LaTeX" in prompt
        assert "Preserve meaningful capitalization" in prompt


def test_mcq_prompt_does_not_request_subjective_final_answer():
    prompt = get_solution_prompt("mcq_sc", "physics")

    assert "Subjective Final Answer Field (REQUIRED)" not in prompt
