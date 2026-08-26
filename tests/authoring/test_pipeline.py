from types import SimpleNamespace

from vbagent.authoring.models import AuthoringRequest
from vbagent.authoring.pipeline import AuthoringPipeline
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
    candidate = AuthoringPipeline(agents=agents).run(_plan().items[0])

    assert candidate.status is CandidateStatus.ACCEPTED
    assert candidate.accepted
    assert "Independently" in candidate.final_latex
    assert "constant acceleration" in candidate.final_latex
    assert all(gate.passed for gate in candidate.gates)
    assert agents.calls == [
        "draft", "solve", "classify", "answer", "alignment",
        "difficulty", "compile", "review",
    ]


def test_invalid_structure_is_rejected_before_expensive_agents():
    agents = FakeAgents()
    agents.problem = r"\item A malformed MCQ without options"

    candidate = AuthoringPipeline(agents=agents).run(_plan().items[0])

    assert candidate.status is CandidateStatus.REJECTED
    assert agents.calls == ["draft"]
    assert candidate.gates[-1].gate == "structure"


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
