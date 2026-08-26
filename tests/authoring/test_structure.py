from vbagent.authoring.models import (
    AuthoringRequest,
    QuestionType,
    SourceKind,
    VariantFamily,
)
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.structure import validate_draft_structure, validate_final_structure


def _spec(question_type: QuestionType, *, passage_questions: int = 3):
    spec = AuthoringPlanner().plan(
        AuthoringRequest(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            question_types={"mcq_sc": 1},
            passage_question_count=passage_questions,
        )
    ).items[0]
    return spec.model_copy(update={"question_type": question_type})


def test_four_option_contract_is_deterministic():
    problem = (
        r"\item Choose."
        "\n"
        r"\begin{tasks}(2)\task A \ans\task B\task C\end{tasks}"
    )
    issues = validate_draft_structure(
        _spec(QuestionType.MCQ_SINGLE),
        problem,
        r"\begin{solution}A\end{solution}",
    )

    assert any("exactly four options" in issue for issue in issues)


def test_integer_contract_rejects_mcq_options():
    problem = (
        r"\item Find the integer. \hrulefill \ansint{2}"
        "\n"
        r"\begin{tasks}(2)\task A\task B\task C\task D\end{tasks}"
    )
    issues = validate_draft_structure(
        _spec(QuestionType.INTEGER),
        problem,
        r"\begin{solution}The result is 2.\end{solution}",
    )

    assert "integer problem must not contain MCQ task options" in issues


def test_passage_contract_validates_each_subquestion():
    problem = r"""\item[] A shared passage.
\item First question.
\begin{tasks}(2)\task A \ans\task B\task C\task D\end{tasks}
\item Second question.
\begin{tasks}(2)\task A\task B\task C\task D\end{tasks}"""
    issues = validate_draft_structure(
        _spec(QuestionType.PASSAGE, passage_questions=2),
        problem,
        r"\begin{solution}Work for both questions.\end{solution}",
    )

    assert any("subquestion 2 must mark exactly one correct option" in issue for issue in issues)


def test_final_contract_rechecks_problem_and_exact_solution_count():
    spec = _spec(QuestionType.MCQ_SINGLE)
    problem = (
        r"\item Choose."
        "\n"
        r"\begin{tasks}(2)\task A \ans\task B \ans\task C\task D\end{tasks}"
    )
    final = problem + "\n" + r"\begin{solution}Work.\end{solution}"

    issues = validate_final_structure(spec, final)

    assert any("exactly one correct option" in issue for issue in issues)


def test_numerical_variant_must_change_numbers_without_changing_blueprint():
    parent = (
        r"\item A 2 kg block moves 4 m."
        "\n"
        r"\begin{tasks}(2)\task 2\task 4 \ans\task 6\task 8\end{tasks}"
    )
    spec = _spec(QuestionType.MCQ_SINGLE).model_copy(
        update={
            "source_kind": SourceKind.VARIANT,
            "variant_family": VariantFamily.NUMERICAL,
            "parent_spec_id": "parent",
            "parent_problem_latex": parent + r"\begin{solution}Work.\end{solution}",
        }
    )
    unchanged_issues = validate_draft_structure(
        spec,
        parent,
        r"\begin{solution}Work.\end{solution}",
    )
    changed_issues = validate_draft_structure(
        spec,
        parent.replace("2 kg", "3 kg").replace("4 m", "5 m"),
        r"\begin{solution}Work.\end{solution}",
    )

    assert any("must change" in issue for issue in unchanged_issues)
    assert not any("numerical variant" in issue for issue in changed_issues)


def test_ambiguous_concatenated_si_units_are_rejected_deterministically():
    spec = _spec(QuestionType.MCQ_SINGLE)
    problem = (
        r"\item A particle moves at $10\ \text{ms}^{-1}$. Choose."
        "\n"
        r"\begin{tasks}(2)\task A \ans\task B\task C\task D\end{tasks}"
    )
    issues = validate_draft_structure(
        spec,
        problem,
        r"\begin{solution}$v=10\ \text{ms}^{-1}$\end{solution}",
    )

    assert any("ambiguous" in issue and "problem" in issue for issue in issues)
    assert any("ambiguous" in issue and "solution" in issue for issue in issues)
