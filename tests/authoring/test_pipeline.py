from types import SimpleNamespace

from vbagent.authoring.models import AuthoringRequest, DiagramPolicy, SourceKind
from vbagent.authoring.pipeline import AuthoringPipeline, _aggregate_usage
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.results import CandidateStatus
from vbagent.models.classification import DifficultyAssessment, PrimaryClassification


class Dumpable(SimpleNamespace):
    def model_dump(self, mode=None):
        return dict(self.__dict__)


class FakeAgents:
    def __init__(self):
        self.calls = []
        self.problem = (
            r"\item A body moves with constant acceleration. Its speed after $2$ s is"
            "\n"
            r"\begin{tasks}(2)"
            "\n"
            r"\task $2$ m/s \task $4$ m/s \ans \task $6$ m/s \task $8$ m/s"
            "\n"
            r"\end{tasks}"
        )
        self.draft_solution = r"\begin{solution}$v=u+at=4\,\mathrm{m/s}$.\end{solution}"
        self.answer_passed = True
        self.alignment_passed = True
        self.classified_type = "mcq_sc"
        self.observed_difficulty = 5.0
        self.compile_success = True
        self.review_passed = True
        self.raise_stage = None
        self.diagram_description = ""

    def _record(self, stage):
        self.calls.append(stage)
        if self.raise_stage == stage:
            raise RuntimeError(f"{stage} unavailable")

    def generate_draft(self, spec):
        self._record("draft")
        return Dumpable(
            problem_latex=self.problem,
            solution_latex=self.draft_solution,
            idea_latex=r"\begin{idea}constant acceleration\end{idea}",
            diagram_description=self.diagram_description,
            generation_metadata={"source": "fake"},
        )

    def generate_problem_diagram(self, spec, problem_latex, description):
        self._record("diagram")
        return {"code": r"\begin{tikzpicture}\draw (0,0)--(1,0);\end{tikzpicture}", "agent": "fake"}

    def solve_independently(self, spec, problem_latex, has_diagram):
        self._record("solve")
        independent = r"\begin{solution}Independently, $v=4\,\mathrm{m/s}$.\end{solution}"
        return Dumpable(
            latex=problem_latex + "\n\n" + independent,
            answer_type="mcq",
            answer_value="b",
            final_answer_latex=None,
        )

    def classify(self, spec, problem_latex):
        self._record("classify")
        return PrimaryClassification(
            subject=spec.subject,
            question_type=self.classified_type,
            has_diagram="tikzpicture" in problem_latex,
            classified_from="latex",
        )

    def verify_answer(self, spec, problem_latex, draft_solution, independent_solution):
        self._record("answer")
        return Dumpable(
            passed=self.answer_passed,
            problem_well_posed=True,
            draft_solution_correct=self.answer_passed,
            independent_solution_correct=True,
            answers_agree=self.answer_passed,
            reasoning="answers agree" if self.answer_passed else "draft and independent answers differ",
        )

    def verify_spec(self, spec, problem_latex, solution_latex):
        self._record("alignment")
        return Dumpable(
            passed=self.alignment_passed,
            topic_aligned=self.alignment_passed,
            reasoning="specification aligned" if self.alignment_passed else "wrong topic",
        )

    def assess_difficulty(self, spec, final_latex, primary):
        self._record("difficulty")
        return DifficultyAssessment(
            difficulty="medium",
            difficulty_score=self.observed_difficulty,
            difficulty_reasoning="independent estimate",
            expected_solve_time_minutes=3,
        )

    def compile(self, spec, final_latex, output_dir=None):
        self._record("compile")
        return {
            "success": self.compile_success,
            "error_summary": "" if self.compile_success else "Undefined control sequence",
            "pdf_path": None,
        }

    def review(self, spec, final_latex):
        self._record("review")
        return Dumpable(
            passed=self.review_passed,
            summary="review passed" if self.review_passed else "solution issue",
            suggestions=[],
        )

    @staticmethod
    def provenance():
        return {"fake": {"model": "test"}}


def _plan(**updates):
    request = {
        "exam": "jee_main",
        "subject": "physics",
        "chapter": "kinematics",
        "topics": ["uniformly accelerated motion"],
        "count": 1,
        "question_types": {"mcq_sc": 1},
        "difficulties": {5: 1},
        "seed": 7,
    }
    request.update(updates)
    return AuthoringPlanner().plan(AuthoringRequest(**request))


def test_complete_pipeline_accepts_only_after_every_gate():
    agents = FakeAgents()
    stages = []
    candidate = AuthoringPipeline(
        agents=agents,
        progress_callback=stages.append,
    ).run(_plan().items[0])

    assert candidate.status is CandidateStatus.ACCEPTED
    assert candidate.accepted
    assert "Independently" in candidate.final_latex
    assert "constant acceleration" in candidate.final_latex
    assert all(gate.passed for gate in candidate.gates)
    assert agents.calls == [
        "draft", "solve", "classify", "answer", "alignment",
        "difficulty", "compile", "review",
    ]
    assert stages == [
        "drafting",
        "validating_draft_structure",
        "solving_independently",
        "validating_final_structure",
        "classifying_problem",
        "adjudicating_answer",
        "checking_syllabus_alignment",
        "assessing_difficulty",
        "compiling_item",
        "reviewing_quality",
        "checking_novelty",
        "finalizing_item",
    ]


def test_idea_only_draft_skips_every_solution_agent_and_is_not_accepted():
    agents = FakeAgents()
    candidate = AuthoringPipeline(agents=agents).run(_plan(include_solution=False).items[0])
    assert agents.calls == ["draft", "compile"]
    assert candidate.status is CandidateStatus.DRAFT
    assert candidate.draft_solution_latex == ""
    assert candidate.independent_solution_latex == ""
    assert r"\begin{solution}" not in candidate.final_latex
    assert r"\begin{idea}" in candidate.final_latex
    assert not candidate.accepted


def test_solution_only_output_has_no_idea_but_keeps_all_validation_gates():
    agents = FakeAgents()
    candidate = AuthoringPipeline(agents=agents).run(_plan(include_idea=False).items[0])
    assert candidate.status is CandidateStatus.ACCEPTED
    assert "solve" in agents.calls
    assert r"\begin{solution}" in candidate.final_latex
    assert r"\begin{idea}" not in candidate.final_latex
    assert candidate.idea_latex == ""


def test_question_only_output_is_a_structural_draft():
    agents = FakeAgents()
    candidate = AuthoringPipeline(agents=agents).run(_plan(include_solution=False, include_idea=False).items[0])
    assert candidate.status is CandidateStatus.DRAFT
    assert candidate.final_latex == agents.problem
    assert agents.calls == ["draft", "compile"]


def test_adding_idea_preserves_existing_solution_and_alternates():
    agents = FakeAgents()
    saved = agents.problem + "\n\n" + agents.draft_solution + (
        "\n\n" + r"\begin{alternatesolution}The author's second method.\end{alternatesolution}"
    )
    spec = _plan().items[0].model_copy(update={
        "source_kind": SourceKind.COMPLETION,
        "parent_spec_id": "original",
        "parent_problem_latex": agents.problem,
        "parent_solution_latex": agents.draft_solution,
        "parent_final_latex": saved,
        "parent_was_accepted": True,
    })
    candidate = AuthoringPipeline(agents=agents).run(spec)
    assert candidate.status is CandidateStatus.ACCEPTED
    assert candidate.final_latex.startswith(saved + "\n\n")
    assert candidate.published_solution_latex == agents.draft_solution
    assert "Independently" in candidate.independent_solution_latex
    assert "Independently" not in candidate.final_latex
    assert candidate.final_latex.count(r"\begin{idea}") == 1


def test_completion_reuses_an_existing_required_diagram():
    agents = FakeAgents()
    agents.problem += "\n" + r"\begin{tikzpicture}\draw (0,0)--(1,0);\end{tikzpicture}"
    spec = _plan().items[0].model_copy(update={
        "source_kind": SourceKind.COMPLETION,
        "diagram_policy": DiagramPolicy.REQUIRED,
        "parent_spec_id": "original",
        "parent_problem_latex": agents.problem,
        "parent_final_latex": agents.problem,
    })
    candidate = AuthoringPipeline(agents=agents).run(spec)
    assert candidate.status is CandidateStatus.ACCEPTED
    assert "diagram" not in agents.calls
    assert candidate.problem_latex == spec.parent_problem_latex
    assert candidate.final_latex.count(r"\begin{tikzpicture}") == 1


def test_invalid_structure_is_rejected_before_expensive_agents():
    agents = FakeAgents()
    agents.problem = r"\item A malformed MCQ without options"

    candidate = AuthoringPipeline(agents=agents).run(_plan().items[0])

    assert candidate.status is CandidateStatus.REJECTED
    assert agents.calls == ["draft"]
    assert candidate.gates[-1].gate == "structure"


def test_pipeline_trace_tag_identifies_item_and_is_restored(monkeypatch):
    from vbagent.ui.logging import _get_tagged_name, agent_task_context

    spec = _plan().items[0]
    agents = FakeAgents()
    original = agents.generate_draft
    observed = []

    def capture_tag(spec):
        observed.append(_get_tagged_name("Draft"))
        return original(spec)

    monkeypatch.setattr(agents, "generate_draft", capture_tag)
    with agent_task_context("parent"):
        AuthoringPipeline(agents=agents).run(spec)
        assert _get_tagged_name("After") == "parent › After"
    assert observed == [f"item 001 · {spec.spec_id[:8]} › Draft"]


def test_final_problem_is_revalidated_after_independent_solution_assembly():
    agents = FakeAgents()

    def solve_with_duplicate_answer(spec, problem_latex, has_diagram):
        agents._record("solve")
        mutated = problem_latex.replace(r"\task $8$ m/s", r"\ans \task $8$ m/s")
        return Dumpable(
            latex=mutated + "\n\n" + r"\begin{solution}Independent work.\end{solution}",
            answer_type="mcq",
            answer_value="b",
            final_answer_latex=None,
        )

    agents.solve_independently = solve_with_duplicate_answer
    candidate = AuthoringPipeline(agents=agents).run(_plan().items[0])

    assert candidate.status is CandidateStatus.REJECTED
    assert candidate.gates[-1].gate == "final_structure"
    assert "exactly one correct option" in candidate.gates[-1].summary
    assert agents.calls == ["draft", "solve"]


def test_independent_classification_mismatch_rejects_candidate():
    agents = FakeAgents()
    agents.classified_type = "subjective"

    candidate = AuthoringPipeline(agents=agents).run(_plan().items[0])

    assert candidate.status is CandidateStatus.REJECTED
    assert candidate.gates[-1].gate == "classification"
    assert agents.calls == ["draft", "solve", "classify"]


def test_answer_disagreement_rejects_without_counting_coverage():
    agents = FakeAgents()
    agents.answer_passed = False

    candidate = AuthoringPipeline(agents=agents).run(_plan().items[0])

    assert candidate.status is CandidateStatus.REJECTED
    assert candidate.gates[-1].gate == "answer_agreement"
    assert "differ" in candidate.gates[-1].summary


def test_spec_drift_and_difficulty_drift_are_hard_gates():
    alignment_agents = FakeAgents()
    alignment_agents.alignment_passed = False
    alignment = AuthoringPipeline(agents=alignment_agents).run(_plan().items[0])
    assert alignment.status is CandidateStatus.REJECTED
    assert alignment.gates[-1].gate == "spec_alignment"

    difficulty_agents = FakeAgents()
    difficulty_agents.observed_difficulty = 8.0
    difficulty = AuthoringPipeline(agents=difficulty_agents).run(_plan().items[0])
    assert difficulty.status is CandidateStatus.REJECTED
    assert difficulty.gates[-1].gate == "difficulty"


def test_compile_failure_and_agent_failure_are_distinct():
    compile_agents = FakeAgents()
    compile_agents.compile_success = False
    compile_candidate = AuthoringPipeline(agents=compile_agents).run(_plan().items[0])
    assert compile_candidate.status is CandidateStatus.REJECTED
    assert compile_candidate.gates[-1].gate == "compile"

    failed_agents = FakeAgents()
    failed_agents.raise_stage = "solve"
    failed_candidate = AuthoringPipeline(agents=failed_agents).run(_plan().items[0])
    assert failed_candidate.status is CandidateStatus.FAILED
    assert failed_candidate.error_stage == "independent_solution"


def test_required_diagram_is_generated_and_placeholder_resolved():
    agents = FakeAgents()
    agents.diagram_description = "A velocity-time graph"
    agents.problem = agents.problem + "\n" + r"\input{diagram}"
    spec = _plan(diagram_ratio=1.0).items[0]

    candidate = AuthoringPipeline(agents=agents).run(spec)

    assert candidate.status is CandidateStatus.ACCEPTED
    assert "diagram" in agents.calls
    assert r"\input{diagram}" not in candidate.final_latex
    assert r"\begin{tikzpicture}" in candidate.final_latex


def test_accepted_only_novelty_index_rejects_repeated_blueprint():
    agents = FakeAgents()
    plan = AuthoringPlanner().plan(
        AuthoringRequest(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["uniformly accelerated motion"],
            count=2,
            question_types={"mcq_sc": 1},
            difficulties={5: 1},
            seed=19,
        )
    )
    pipeline = AuthoringPipeline(agents=agents)

    first = pipeline.run(plan.items[0])
    second = pipeline.run(plan.items[1])

    assert first.status is CandidateStatus.ACCEPTED
    assert second.status is CandidateStatus.REJECTED
    assert second.gates[-1].gate == "novelty"
    assert second.gates[-1].data["closest_id"] == first.spec.spec_id


def test_human_review_policy_never_auto_accepts_or_updates_novelty():
    plan = _plan(acceptance={"human_review_required": True})
    pipeline = AuthoringPipeline(agents=FakeAgents())

    candidate = pipeline.run(plan.items[0])

    assert candidate.status is CandidateStatus.NEEDS_REVIEW
    assert len(pipeline.novelty_index) == 0


def test_usage_aggregation_preserves_cache_profile_provenance():
    events = [
        {
            "event": "completed",
            "agent": "Draft",
            "stage": "draft",
            "model": "gpt-5.6-sol",
            "duration": 2.0,
            "request_duration": 1.8,
            "queue_duration": 0.2,
            "key_name": "profile-b",
            "cache_domain": "org-main:global",
            "cache_group_id": "draft:s1of4",
            "response_id": "resp-one",
            "tokens": {
                "requests": 1,
                "input": 1000,
                "output": 100,
                "cached": 600,
                "cache_write": 200,
                "ordinary_input": 200,
                "cache_read_requests": 1,
                "cache_reported_requests": 1,
                "cache_metrics_reported": True,
                "effective_input_multiplier": 0.51,
                "reasoning": 50,
            },
        },
        {
            "event": "profile_failover",
            "agent": "Draft",
            "key_name": "profile-a",
        },
    ]

    usage = _aggregate_usage(events)

    assert usage["totals"]["cache_hit_percent"] == 60.0
    assert usage["totals"]["cache_write_percent"] == 20.0
    assert usage["totals"]["cache_request_hit_percent"] == 100.0
    assert usage["totals"]["effective_input_multiplier"] == 0.51
    assert usage["totals"]["profile_failovers"] == 1
    assert usage["profiles"] == {"profile-b": 1}
    assert usage["cache_domains"] == {"org-main:global": 1}
    assert usage["profile_usage"]["profile-b"]["cache_hit_percent"] == 60.0
    assert usage["profile_usage"]["profile-a"]["failovers"] == 1
    assert (
        usage["cache_domain_usage"]["org-main:global"]["cache_write_percent"]
        == 20.0
    )
    assert usage["agents"][0]["response_id"] == "resp-one"


def test_effective_input_multiplier_is_unknown_for_mixed_model_usage():
    events = [
        {
            "event": "completed",
            "agent": "GPT56",
            "model": "gpt-5.6-sol",
            "tokens": {
                "requests": 1,
                "input": 100,
                "ordinary_input": 100,
                "cache_metrics_reported": True,
                "effective_input_multiplier": 1.0,
            },
        },
        {
            "event": "completed",
            "agent": "Other",
            "model": "other-model",
            "tokens": {
                "requests": 1,
                "input": 100,
                "ordinary_input": 100,
                "cache_metrics_reported": True,
                "effective_input_multiplier": None,
            },
        },
    ]

    assert _aggregate_usage(events)["totals"]["effective_input_multiplier"] is None
