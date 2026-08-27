from types import SimpleNamespace

import pytest

from vbagent.authoring.agents import DefaultAuthoringAgents
from vbagent.authoring.models import AuthoringRequest, SourceKind, VariantFamily
from vbagent.authoring.planner import AuthoringPlanner


def component_spec(**updates):
    spec = (
        AuthoringPlanner()
        .plan(
            AuthoringRequest(
                exam="jee_main",
                subject="physics",
                chapter="kinematics",
                count=1,
            )
        )
        .items[0]
    )
    return spec.model_copy(update=updates)


def test_original_generator_receives_component_flags(monkeypatch):
    received = {}

    def generate(**kwargs):
        received.update(kwargs)
        return SimpleNamespace(
            problem_latex="question", solution_latex="", idea_latex="idea"
        )

    monkeypatch.setattr(
        "vbagent.agents.content_generation.idea_generator.generate_from_idea", generate
    )
    DefaultAuthoringAgents().generate_draft(
        component_spec(include_solution=False, include_idea=True)
    )
    assert received["include_solution"] is False
    assert received["include_idea"] is True


def test_adding_only_an_idea_does_not_invoke_a_solver(monkeypatch):
    agents = DefaultAuthoringAgents()
    monkeypatch.setattr(
        agents, "solve_independently", lambda *_: pytest.fail("unexpected solver call")
    )
    monkeypatch.setattr(
        "vbagent.agents.content_generation.idea.generate_idea_latex",
        lambda *_args, **_kwargs: r"\begin{idea}Use the domain.\end{idea}",
    )
    result = agents.generate_draft(
        component_spec(
            source_kind=SourceKind.COMPLETION,
            parent_spec_id="parent",
            parent_problem_latex=r"\item Existing question",
            include_solution=False,
        )
    )
    assert result.problem_latex == r"\item Existing question"
    assert result.solution_latex == ""
    assert "Use the domain" in result.idea_latex


@pytest.mark.parametrize(
    "include_solution,include_idea", [(False, True), (True, False), (False, False)]
)
def test_variant_generator_honors_selected_components(
    monkeypatch, include_solution, include_idea
):
    from vbagent.agents.variants import variant

    calls = []
    question = r"\item Variant question"
    solution = r"\begin{solution}Worked answer.\end{solution}"
    idea = r"\begin{idea}Conceptual hint.\end{idea}"
    output = (
        question
        + (solution if include_solution else "")
        + (idea if include_idea else "")
    )

    def run(agent, message):
        calls.append((agent.instructions, message))
        return output

    monkeypatch.setattr(variant, "get_context_prompt_section", lambda *_: "")
    monkeypatch.setattr(variant, "run_agent_sync", run)
    result = DefaultAuthoringAgents().generate_draft(
        component_spec(
            source_kind=SourceKind.VARIANT,
            variant_family=VariantFamily.CONTEXT,
            parent_spec_id="parent",
            parent_problem_latex=r"\item Existing question",
            include_solution=include_solution,
            include_idea=include_idea,
        )
    )
    assert result.problem_latex == question
    assert result.solution_latex == (solution if include_solution else "")
    assert result.idea_latex == (idea if include_idea else "")
    assert len(calls) == 1
    assert "overrides the default output format" in calls[0][0]
    assert f"include_solution={str(include_solution).lower()}" in calls[0][1]
    assert f"include_idea={str(include_idea).lower()}" in calls[0][1]
