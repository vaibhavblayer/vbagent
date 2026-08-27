"""Deterministic structure checks for generated problem artifacts."""

from __future__ import annotations

import re

from vbagent.authoring.models import (
    DiagramPolicy,
    GenerationSpec,
    QuestionType,
    SourceKind,
    VariantFamily,
)
from vbagent.authoring.novelty import variant_stem_similarity
from vbagent.pipeline.io import has_main_diagram_placeholder

_VISUAL_RE = re.compile(
    r"\\(?:begin\{(?:tikzpicture|circuitikz|axis)\}|includegraphics)",
    flags=re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?")
_AMBIGUOUS_SI_UNIT_RE = re.compile(
    r"\\text\{\s*ms\s*\}\s*\^\{?\s*-[12]\s*\}?",
    flags=re.IGNORECASE,
)


def validate_draft_structure(
    spec: GenerationSpec,
    problem_latex: str,
    solution_latex: str,
    diagram_description: str = "",
) -> list[str]:
    """Return deterministic contract violations without invoking an agent."""
    issues = _validate_problem_structure(
        spec,
        problem_latex,
        diagram_description,
        final=spec.source_kind is SourceKind.COMPLETION,
    )
    if not spec.include_solution:
        if solution_latex.strip():
            issues.append("solution was deferred and must be empty")
        return issues
    solution = solution_latex.strip()
    solution_starts = len(re.findall(r"\\begin\{solution\}", solution))
    solution_ends = len(re.findall(r"\\end\{solution\}", solution))
    if solution_starts != 1 or solution_ends != 1:
        issues.append("draft solution must contain exactly one complete solution environment")
    if _AMBIGUOUS_SI_UNIT_RE.search(solution):
        issues.append(
            "draft solution uses ambiguous \\text{ms}^{-n} units; "
            "write \\mathrm{m/s} or \\mathrm{m/s^2}"
        )
    return issues


def _validate_problem_structure(
    spec: GenerationSpec,
    problem_latex: str,
    diagram_description: str = "",
    *,
    final: bool = False,
) -> list[str]:
    """Validate the question portion shared by draft and final artifacts."""
    issues: list[str] = []
    problem = problem_latex.strip()
    qtype = spec.question_type

    if not problem:
        issues.append("problem_latex is empty")
        return issues
    if not re.search(r"\\item(?:\[|\b)", problem):
        issues.append("problem_latex must contain a top-level \\item")
    if r"\documentclass" in problem or r"\begin{document}" in problem:
        issues.append("problem_latex must be a snippet, not a complete document")
    if re.search(r"\\begin\{solution\}", problem):
        issues.append("problem_latex must not contain a solution environment")
    if _AMBIGUOUS_SI_UNIT_RE.search(problem):
        issues.append(
            "problem uses ambiguous \\text{ms}^{-n} units; "
            "write \\mathrm{m/s} or \\mathrm{m/s^2}"
        )

    if (
        spec.source_kind is SourceKind.VARIANT
        and spec.variant_family is VariantFamily.NUMERICAL
    ):
        parent_problem = re.split(
            r"\\begin\{(?:solution|idea)\}",
            spec.parent_problem_latex,
            maxsplit=1,
        )[0]
        if not parent_problem.strip():
            issues.append("numerical variant is missing its accepted parent problem")
        else:
            parent_numbers = _NUMBER_RE.findall(parent_problem)
            candidate_numbers = _NUMBER_RE.findall(problem)
            if parent_numbers == candidate_numbers:
                issues.append("numerical variant must change the parent problem's numerical values")
            similarity = variant_stem_similarity(parent_problem, problem)
            if similarity < 0.90:
                issues.append(
                    "numerical variant changed more than numerical values; "
                    f"parent stem similarity is {similarity:.3f}"
                )

    task_environments = len(re.findall(r"\\begin\{tasks\}", problem))
    task_count = len(re.findall(r"\\task\b", problem))
    answer_markers = len(re.findall(r"\\ans\b", problem))
    integer_markers = len(re.findall(r"\\ansint\{[^}]+\}", problem))

    four_option_types = {
        QuestionType.MCQ_SINGLE,
        QuestionType.MCQ_MULTIPLE,
        QuestionType.ASSERTION_REASON,
        QuestionType.MATCH,
    }
    if qtype in four_option_types:
        if task_environments != 1:
            issues.append(f"{qtype.value} problem must contain exactly one tasks environment")
        if task_count != 4:
            issues.append(f"{qtype.value} problem must contain exactly four options; found {task_count}")
    elif qtype in {QuestionType.SUBJECTIVE, QuestionType.INTEGER} and task_count:
        issues.append(f"{qtype.value} problem must not contain MCQ task options")
    if qtype is QuestionType.MCQ_SINGLE and answer_markers != 1:
        issues.append("mcq_sc problem must mark exactly one correct option with \\ans")
    if qtype is QuestionType.MCQ_MULTIPLE and not 2 <= answer_markers <= 4:
        issues.append("mcq_mc problem must mark two to four correct options with \\ans")
    if qtype in {QuestionType.ASSERTION_REASON, QuestionType.MATCH} and answer_markers != 1:
        issues.append(f"{qtype.value} problem must mark exactly one correct option with \\ans")
    if qtype is QuestionType.INTEGER and integer_markers != 1:
        issues.append("integer problem must contain exactly one \\ansint{...} marker")
    if qtype is not QuestionType.INTEGER and integer_markers:
        issues.append(f"{qtype.value} problem must not contain an integer answer marker")
    if qtype is QuestionType.ASSERTION_REASON:
        if not re.search(r"Assertion\s*\(?A\)?", problem, re.IGNORECASE):
            issues.append("assertion_reason problem is missing Assertion (A)")
        if not re.search(r"Reason\s*\(?R\)?", problem, re.IGNORECASE):
            issues.append("assertion_reason problem is missing Reason (R)")
    if qtype is QuestionType.MATCH:
        if not re.search(r"List\s*I", problem, re.IGNORECASE):
            issues.append("match problem is missing List I")
        if not re.search(r"List\s*II", problem, re.IGNORECASE):
            issues.append("match problem is missing List II")
    if qtype is QuestionType.PASSAGE:
        item_matches = list(re.finditer(r"(?m)^\s*\\item(?:\[[^]]*\])?", problem))
        item_count = len(item_matches)
        expected_items = spec.passage_question_count + 1
        if item_count != expected_items:
            issues.append(
                f"passage problem must contain one header and exactly "
                f"{spec.passage_question_count} subquestions; found {max(0, item_count - 1)}"
            )
        else:
            for index in range(1, item_count):
                end = item_matches[index + 1].start() if index + 1 < item_count else len(problem)
                subquestion = problem[item_matches[index].start():end]
                sub_tasks = len(re.findall(r"\\task\b", subquestion))
                sub_answers = len(re.findall(r"\\ans\b", subquestion))
                if sub_tasks != 4:
                    issues.append(
                        f"passage subquestion {index} must contain exactly four options; "
                        f"found {sub_tasks}"
                    )
                if sub_answers != 1:
                    issues.append(
                        f"passage subquestion {index} must mark exactly one correct option; "
                        f"found {sub_answers}"
                    )

    has_placeholder = has_main_diagram_placeholder(problem)
    has_visual = bool(_VISUAL_RE.search(problem))
    has_description = bool(diagram_description.strip())
    if spec.diagram_policy is DiagramPolicy.REQUIRED:
        if final:
            if not has_visual:
                issues.append("final problem is missing its required assembled diagram")
        else:
            if not has_description:
                issues.append("diagram policy is required but no diagram description was generated")
            if not has_placeholder:
                issues.append("diagram policy is required but the main diagram placeholder is missing")
    if spec.diagram_policy is DiagramPolicy.FORBIDDEN and (
        has_description or has_visual or has_placeholder
    ):
        issues.append("diagram policy is forbidden but the draft requested or embedded a diagram")
    return issues


def validate_final_structure(spec: GenerationSpec, final_latex: str) -> list[str]:
    """Validate both the independent solution and final question representation."""
    issues: list[str] = []
    if not spec.include_solution:
        if re.search(r"\\begin\{(?:solution|alternatesolution)\}", final_latex):
            issues.append("deferred-solution draft contains a solution")
        question = re.split(r"\\begin\{idea\}", final_latex, maxsplit=1)[0]
        issues.extend(_validate_problem_structure(spec, question, final=True))
        return issues
    solution_starts = list(re.finditer(r"\\begin\{solution\}", final_latex))
    solution_ends = list(re.finditer(r"\\end\{solution\}", final_latex))
    if len(solution_starts) != 1 or len(solution_ends) != 1:
        issues.append("final artifact must contain exactly one complete independent solution environment")
    elif solution_starts[0].start() >= solution_ends[0].start():
        issues.append("final artifact has no complete independent solution environment")
    else:
        problem_latex = final_latex[:solution_starts[0].start()]
        issues.extend(_validate_problem_structure(spec, problem_latex, final=True))
        solution_latex = final_latex[solution_starts[0].start():solution_ends[0].end()]
        if _AMBIGUOUS_SI_UNIT_RE.search(solution_latex):
            issues.append(
                "final solution uses ambiguous \\text{ms}^{-n} units; "
                "write \\mathrm{m/s} or \\mathrm{m/s^2}"
            )
    if r"\input{diagram}" in final_latex or re.search(r"\\text\s*\{\s*\[\s*diagram", final_latex, re.I):
        issues.append("final artifact contains an unresolved main diagram placeholder")
    return issues
