"""Adapters from canonical authoring stages to the existing agent workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from vbagent.authoring.models import GenerationSpec


class DefaultAuthoringAgents:
    """Use existing vbagent agents behind a stable authoring-stage API."""

    def generate_draft(self, spec: GenerationSpec, retry_context: str | None = None):
        if spec.source_kind.value == "variant":
            return self._generate_variant_draft(spec, retry_context=retry_context)

        from vbagent.agents.content_generation.idea_generator import generate_from_idea

        ideas = list(spec.seed_ideas) or [
            (
                f"Create an original {spec.construction_family} problem about the exact "
                f"syllabus topic through a {spec.reasoning_lens} lens"
            )
        ]
        concepts = list(spec.required_concepts) or [spec.topic]
        return generate_from_idea(
            ideas=ideas,
            concepts=concepts,
            topic=spec.topic,
            difficulty=spec.difficulty_band,
            question_type=spec.question_type.value,
            subject=spec.subject,
            exam=spec.exam,
            exam_pattern_description=spec.exam_pattern_description,
            chapter=spec.chapter,
            chapter_description=spec.chapter_description,
            syllabus_topic=spec.topic,
            syllabus_topic_description=spec.topic_description,
            difficulty_score=spec.difficulty,
            cognitive_level=spec.cognitive_level.value,
            reasoning_lens=spec.reasoning_lens,
            representation=spec.representation.value,
            construction_family=spec.construction_family,
            diagram_policy=spec.diagram_policy.value,
            forbidden_concepts=list(spec.forbidden_concepts),
            tone=spec.tone,
            random_seed=spec.random_seed,
            retry_feedback=retry_context,
            passage_question_count=spec.passage_question_count,
        )

    @staticmethod
    def _generate_variant_draft(spec: GenerationSpec, retry_context: str | None = None):
        import re

        from vbagent.agents.variants.variant import generate_variant
        from vbagent.models.classification import GeneratedProblem

        if spec.variant_family is None:
            raise ValueError("variant spec has no variant_family")
        source = spec.parent_problem_latex
        if retry_context:
            source += (
                "\n\n% Retry evidence for the generator: "
                + retry_context.replace("\n", " ")
            )
        generated = generate_variant(
            source_latex=source,
            variant_type=spec.variant_family.value,
            use_context=True,
        )
        solution_match = re.search(
            r"\\begin\{solution\}.*?\\end\{solution\}",
            generated,
            flags=re.DOTALL,
        )
        if not solution_match:
            raise ValueError("variant agent returned no complete solution environment")
        problem = generated[: solution_match.start()].strip()
        solution = solution_match.group(0).strip()
        return GeneratedProblem(
            problem_latex=problem,
            solution_latex=solution,
            idea_latex=(
                "\\begin{idea}\n"
                f"Controlled {spec.variant_family.value} variant of accepted parent "
                f"{spec.parent_spec_id}.\n"
                "\\end{idea}"
            ),
            diagram_description=None,
            generation_metadata={
                "source_kind": "variant",
                "variant_family": spec.variant_family.value,
                "parent_spec_id": spec.parent_spec_id,
                "lineage_root_spec_id": spec.lineage_root_spec_id,
                "lineage_depth": spec.lineage_depth,
            },
        )

    def generate_problem_diagram(self, spec: GenerationSpec, problem_latex: str, description: str) -> dict[str, str]:
        from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
        from vbagent.models.classification import PrimaryClassification

        primary = PrimaryClassification(
            subject=spec.subject,
            question_type=spec.question_type.value,
            has_diagram=True,
            chapter=spec.chapter,
            topic=spec.topic,
            confidence=1.0,
            classified_from="latex",
        )
        code, agent = generate_tikz_with_routing(
            description=description,
            primary=primary,
            subject=spec.subject,
            problem_text=problem_latex,
            use_context=True,
            show_spinner=True,
            diagram_context="problem",
        )
        return {"code": code, "agent": str(agent)}

    def solve_independently(self, spec: GenerationSpec, problem_latex: str, has_diagram: bool):
        from vbagent.agents.orchestration.solution_orchestrator import create_solution_orchestrator

        return create_solution_orchestrator().run(
            problem_latex=problem_latex,
            subject=spec.subject,
            question_type=spec.question_type.value,
            chapter=spec.chapter,
            topic=spec.topic,
            has_diagram=has_diagram,
            image_path=None,
            generate_diagrams=True,
        )

    def classify(self, spec: GenerationSpec, problem_latex: str):
        from vbagent.agents.classification.latex_classifier import classify_from_latex

        return classify_from_latex(problem_latex, subject=spec.subject)

    def verify_answer(self, spec: GenerationSpec, problem_latex: str, draft_solution: str, independent_solution: str):
        from vbagent.agents.quality.answer_agreement import verify_answer_agreement

        return verify_answer_agreement(
            subject=spec.subject,
            question_type=spec.question_type.value,
            problem_latex=problem_latex,
            draft_solution_latex=draft_solution,
            independent_solution_latex=independent_solution,
        )

    def verify_spec(self, spec: GenerationSpec, problem_latex: str, solution_latex: str):
        from vbagent.agents.quality.spec_alignment import verify_spec_alignment

        return verify_spec_alignment(
            exam=spec.exam,
            subject=spec.subject,
            chapter=spec.chapter,
            chapter_description=spec.chapter_description,
            topic=spec.topic,
            topic_description=spec.topic_description,
            question_type=spec.question_type.value,
            cognitive_level=spec.cognitive_level.value,
            representation=spec.representation.value,
            reasoning_lens=spec.reasoning_lens,
            construction_family=spec.construction_family,
            exam_pattern_description=spec.exam_pattern_description,
            exam_pattern_source_url=spec.exam_pattern_source_url,
            required_concepts=spec.required_concepts,
            forbidden_concepts=spec.forbidden_concepts,
            problem_latex=problem_latex,
            solution_latex=solution_latex,
        )

    def assess_difficulty(self, spec: GenerationSpec, final_latex: str, primary):
        from vbagent.agents.classification.difficulty_assessor import assess_difficulty

        primary = primary.model_copy(
            update={
                "chapter": spec.chapter,
                "topic": spec.topic,
                "has_diagram": bool("\\begin{tikzpicture}" in final_latex or "\\includegraphics" in final_latex),
            }
        )
        return assess_difficulty(
            latex_content=final_latex,
            primary=primary,
            subject=spec.subject,
            show_spinner=True,
            exam=spec.exam,
            exam_pattern_description=spec.exam_pattern_description,
            target_difficulty_score=spec.difficulty,
        )

    def compile(self, spec: GenerationSpec, final_latex: str, output_dir: str | None = None) -> dict[str, Any]:
        from vbagent.compile import compile_latex

        result = compile_latex(final_latex, subject=spec.subject, output_dir=output_dir)
        return {
            "success": result.success,
            "error_summary": result.error_summary,
            "pdf_path": result.pdf_path,
        }

    def review(self, spec: GenerationSpec, final_latex: str):
        from vbagent.agents.quality.reviewer import review_problem_sync
        from vbagent.agents.selection.selector import ProblemContext

        is_variant = spec.source_kind.value == "variant"
        variant_name = spec.variant_family.value if spec.variant_family else "derived"
        context = ProblemContext(
            problem_id=spec.spec_id,
            base_path=Path("."),
            image_path=None,
            latex_path=(
                f"{spec.parent_spec_id}.tex"
                if is_variant
                else f"{spec.spec_id}.tex"
            ),
            latex_content=(
                spec.parent_problem_latex
                if is_variant
                else final_latex
            ),
            subject=spec.subject,
            variants={variant_name: final_latex} if is_variant else {},
            variant_paths={variant_name: f"{spec.spec_id}.tex"} if is_variant else {},
        )
        return review_problem_sync(context)

    @staticmethod
    def provenance() -> dict[str, Any]:
        from vbagent.config import get_config

        config = get_config()
        agent_types = {
            "draft": "idea",
            "independent_solution": "solution",
            "classification": "classifier",
            "answer_agreement": "solution_checker",
            "spec_alignment": "taxonomy_classifier",
            "difficulty": "difficulty_assessor",
            "review": "reviewer",
        }
        return {
            stage: {
                "agent_type": agent_type,
                "model": config.get_model(agent_type),
                "reasoning_effort": config.get_agent_config(agent_type).reasoning_effort,
            }
            for stage, agent_type in agent_types.items()
        }
