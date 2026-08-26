from types import SimpleNamespace

from vbagent.authoring.agents import DefaultAuthoringAgents
from vbagent.authoring.models import AuthoringRequest, SourceKind, VariantFamily
from vbagent.authoring.planner import AuthoringPlanner


def _spec():
    return AuthoringPlanner().plan(
        AuthoringRequest(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            question_types={"mcq_sc": 1},
            difficulties={5: 1},
        )
    ).items[0]


def test_exam_pattern_contract_reaches_generation_verification_and_difficulty(monkeypatch):
    spec = _spec()
    calls = {}

    def fake_generate(**kwargs):
        calls["generate"] = kwargs
        return SimpleNamespace()

    def fake_verify(**kwargs):
        calls["verify"] = kwargs
        return SimpleNamespace()

    def fake_difficulty(**kwargs):
        calls["difficulty"] = kwargs
        return SimpleNamespace()

    monkeypatch.setattr(
        "vbagent.agents.content_generation.idea_generator.generate_from_idea",
        fake_generate,
    )
    monkeypatch.setattr(
        "vbagent.agents.quality.spec_alignment.verify_spec_alignment",
        fake_verify,
    )
    monkeypatch.setattr(
        "vbagent.agents.classification.difficulty_assessor.assess_difficulty",
        fake_difficulty,
    )

    agents = DefaultAuthoringAgents()
    agents.generate_draft(spec)
    agents.verify_spec(spec, r"\item Problem", r"\begin{solution}Work\end{solution}")
    primary = SimpleNamespace(
        model_copy=lambda update: SimpleNamespace(**update)
    )
    agents.assess_difficulty(spec, r"\item Problem", primary)

    assert "nearest integer" in calls["generate"]["exam_pattern_description"]
    assert calls["verify"]["exam_pattern_description"] == spec.exam_pattern_description
    assert calls["difficulty"]["exam"] == "jee_main"
    assert calls["difficulty"]["target_difficulty_score"] == 5


def test_problem_diagram_adapter_uses_current_primary_classification_schema(monkeypatch):
    spec = _spec().model_copy(update={"diagram_policy": "required"})
    calls = {}

    def fake_route(**kwargs):
        calls.update(kwargs)
        return r"\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}", "graph"

    monkeypatch.setattr(
        "vbagent.agents.diagram.tikz_router.generate_tikz_with_routing",
        fake_route,
    )

    result = DefaultAuthoringAgents().generate_problem_diagram(
        spec,
        r"\item Interpret the graph.\input{diagram}",
        "A straight velocity-time graph",
    )

    assert result["agent"] == "graph"
    assert calls["primary"].chapter == spec.chapter
    assert calls["primary"].topic == spec.topic
    assert set(calls["primary"].model_dump()) == {
        "subject",
        "question_type",
        "has_diagram",
        "chapter",
        "topic",
        "confidence",
        "classified_from",
        "classified_at",
    }


def test_variant_reviewer_receives_parent_and_declared_child(monkeypatch):
    spec = _spec().model_copy(
        update={
            "source_kind": SourceKind.VARIANT,
            "variant_family": VariantFamily.NUMERICAL,
            "parent_spec_id": "accepted-parent",
            "parent_problem_latex": r"\item Parent\begin{solution}Parent work\end{solution}",
        }
    )
    seen = {}

    def fake_review(context):
        seen["context"] = context
        return SimpleNamespace(passed=True)

    monkeypatch.setattr(
        "vbagent.agents.quality.reviewer.review_problem_sync",
        fake_review,
    )

    child = r"\item Child\begin{solution}Child work\end{solution}"
    DefaultAuthoringAgents().review(spec, child)

    context = seen["context"]
    assert context.latex_content == spec.parent_problem_latex
    assert context.latex_path == "accepted-parent.tex"
    assert context.variants == {"numerical": child}
    assert context.variant_paths == {"numerical": f"{spec.spec_id}.tex"}
