"""ProblemGenerator — thin wrapper over existing agents."""

from __future__ import annotations

from typing import Optional

from .models import GeneratedProblemResult, GenerationTarget


class ProblemGenerator:
    """Selects strategy and delegates to existing agents."""

    def __init__(self, config=None, console=None):
        self.config = config
        self.console = console

    def generate(
        self,
        target: GenerationTarget,
        seed_problems: Optional[list[str]] = None,
        with_solution: bool = True,
        tone: str = "",
        avoid_subtopics: Optional[list[str]] = None,
    ) -> GeneratedProblemResult:
        strategy = target.strategy

        if strategy == "cross_topic" and seed_problems:
            return self._via_cross_topic(target, seed_problems[0])
        elif strategy == "combiner" and seed_problems and len(seed_problems) >= 2:
            return self._via_combiner(target, seed_problems)
        else:
            return self._via_idea_generator(target, with_solution, tone, avoid_subtopics)

    # ------------------------------------------------------------------

    def _via_idea_generator(self, target: GenerationTarget, with_solution: bool, tone: str = "", avoid_subtopics: Optional[list[str]] = None) -> GeneratedProblemResult:
        from vbagent.agents.classification.idea_generator import generate_from_idea
        from vbagent.config import get_config

        subject = get_config().subject
        ideas = target.seed_ideas or [f"{target.topic} problem"]
        concepts = target.concepts or [target.topic]

        # Resolve tone: if it's a preset name, expand to full description
        if tone:
            from .models import TONE_PRESETS
            subject_presets = TONE_PRESETS.get(subject, {})
            resolved_tone = subject_presets.get(tone, tone)  # fallback to raw string if not a preset
            ideas = [f"[Tone: {resolved_tone}] {idea}" for idea in ideas]

        # Inject diversity constraint: avoid already-covered subtopics
        if avoid_subtopics:
            avoid_str = ", ".join(avoid_subtopics)
            ideas = [f"{idea} [IMPORTANT: Avoid these subtopics already covered: {avoid_str}. Pick a DIFFERENT subtopic within {target.topic}.]" for idea in ideas]

        result = generate_from_idea(
            ideas=ideas, concepts=concepts, topic=target.topic,
            difficulty=target.difficulty, question_type=target.question_type,
            subject=subject,
        )

        problem = result.problem_latex
        solution = result.solution_latex if with_solution else ""
        combined = problem + "\n\n" + solution if solution else problem

        # Capture diagram description from idea generator if present
        diagram_desc = getattr(result, "diagram_description", None) or ""
        if not isinstance(diagram_desc, str):
            diagram_desc = ""

        return GeneratedProblemResult(
            problem_tex=problem, solution_tex=solution,
            combined_tex=combined, target=target,
            strategy_used="idea_generator",
            diagram_description=diagram_desc,
        )

    def _via_cross_topic(self, target: GenerationTarget, source_latex: str) -> GeneratedProblemResult:
        from vbagent.agents.variants.cross_topic import (
            analyze_cross_topic, generate_cross_topic_variant,
        )
        from vbagent.config import get_config

        subject = get_config().subject
        analysis = analyze_cross_topic(
            source_latex=source_latex, subject=subject,
            topic=target.topic, question_type=target.question_type,
        )
        variant_latex = generate_cross_topic_variant(source_latex, analysis)

        return GeneratedProblemResult(
            problem_tex=variant_latex, solution_tex="",
            combined_tex=variant_latex, target=target,
            strategy_used="cross_topic",
        )

    def _via_combiner(self, target: GenerationTarget, seed_problems: list[str]) -> GeneratedProblemResult:
        from vbagent.agents.classification.problem_combiner import combine_problems

        problems = [
            {"id": i, "latex": tex, "subject": target.topic, "topic": target.topic}
            for i, tex in enumerate(seed_problems, 1)
        ]
        result = combine_problems(problems, target_difficulty=target.difficulty)

        return GeneratedProblemResult(
            problem_tex=result.combined_problem_latex,
            solution_tex=result.combined_solution_latex,
            combined_tex=result.combined_problem_latex + "\n\n" + result.combined_solution_latex,
            target=target, strategy_used="combiner",
        )
