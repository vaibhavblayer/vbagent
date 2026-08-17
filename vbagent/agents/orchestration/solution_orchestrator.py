"""Solution Orchestrator — subject-aware solution generation.

Flow:
    problem_latex + classification → Subject Agent (1 LLM call)
    → diagram dispatch (parallel, if needed) → stitch + answer marking
"""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Optional


class SolutionResult:
    """Result from the solution orchestrator."""

    __slots__ = (
        "latex", "diagram_codes", "answer_type", "answer_value",
        "final_answer_latex",
        "alternate_solution_recommended", "alternate_solution_hint", "metadata",
    )

    def __init__(
        self,
        latex: str,
        diagram_codes: dict[str, str] | None = None,
        answer_type: str = "subjective",
        answer_value: str | None = None,
        final_answer_latex: str | None = None,
        metadata: dict | None = None,
        alternate_solution_recommended: bool = False,
        alternate_solution_hint: str | None = None,
    ):
        self.latex = latex
        self.diagram_codes = diagram_codes or {}
        self.answer_type = answer_type
        self.answer_value = answer_value
        self.final_answer_latex = final_answer_latex
        self.alternate_solution_recommended = alternate_solution_recommended
        self.alternate_solution_hint = alternate_solution_hint
        self.metadata = metadata or {}


class SolutionOrchestrator:
    """Orchestrates solution generation using subject-specific agents.

    1. Route to subject agent (physics/chemistry/mathematics)
    2. Dispatch diagram agents in parallel (if diagram_requirements)
    3. Stitch diagram TikZ into placeholders
    4. Mark answer (\\ans for MCQ, \\ansint{N} for integer)
    """

    def __init__(self, console=None):
        from vbagent.cli.common import _get_console
        self.console = console or _get_console()
        from vbagent.ui.logging import AgentLoggingContext, capture_agent_logging_context
        captured = capture_agent_logging_context()
        self._logging_context = AgentLoggingContext(
            console=self.console,
            quiet=captured.quiet,
        )

    def run(
        self,
        problem_latex: str,
        subject: str,
        question_type: str,
        chapter: Optional[str] = None,
        topic: Optional[str] = None,
        has_diagram: bool = False,
        image_path: Optional[str] = None,
        generate_diagrams: bool = True,
    ) -> SolutionResult:
        """Generate a complete solution.

        Args:
            problem_latex: Scanned problem LaTeX from ProblemOrchestrator.
            subject: physics, chemistry, mathematics.
            question_type: mcq_sc, mcq_mc, subjective, etc.
            chapter: Chapter/topic area for topic-specific routing.
            topic: Specific topic for topic-specific routing.
            has_diagram: Whether the original problem has a diagram.
            image_path: Path to original image (passed to solver only if has_diagram).
            generate_diagrams: Whether to dispatch solution diagram agents.

        Returns:
            SolutionResult with final LaTeX including solution block.
        """
        # Step 1: Call subject agent
        self.console.print(f"[bold green]Generating {subject} solution...[/bold green]")
        solution_output = self._call_subject_agent(
            problem_latex, subject, question_type, chapter, topic,
            image_path=image_path if has_diagram else None,
        )
        self.console.print("[green]OK[/green] Solution generated")

        solution_latex = solution_output.solution_latex
        diagram_reqs = solution_output.diagram_requirements

        # Step 2: Dispatch diagram agents (parallel)
        diagram_codes: dict[str, str] = {}
        if diagram_reqs and generate_diagrams:
            self.console.print(f"[dim]  → Generating {len(diagram_reqs)} solution diagram(s)...[/dim]")
            diagram_codes = self._dispatch_diagrams(
                diagram_reqs, image_path if has_diagram else None, subject,
            )
            self.console.print(f"[green]  OK {len(diagram_codes)} diagram(s) generated[/green]")
        elif diagram_reqs and not generate_diagrams:
            self.console.print(
                f"[dim]  → Skipping {len(diagram_reqs)} solution diagram agent(s)[/dim]"
            )
            # Do not leave unusable placeholders in a solution when diagram
            # generation was explicitly disabled. Inline TikZ emitted directly
            # by the solution agent is intentionally preserved.
            solution_latex = self._remove_diagram_placeholders(solution_latex)

        # Step 3: Stitch diagrams into placeholders, with a safe fallback when
        # the model returned a requirement but forgot its marker.
        if diagram_codes:
            solution_latex = self._stitch_diagrams(
                solution_latex,
                diagram_codes,
                diagram_requirements=diagram_reqs,
            )
            assembled_count = sum(
                bool(code and code.strip() in solution_latex)
                for code in diagram_codes.values()
            )
            self.console.print(
                f"[green]  OK {assembled_count}/{len(diagram_codes)} "
                "diagram(s) assembled into solution[/green]"
            )
        else:
            assembled_count = 0

        # Step 4: Answer marking
        answer_type = solution_output.answer_type
        answer_value = solution_output.answer_value
        final_answer_latex = getattr(solution_output, "final_answer_latex", None)
        if final_answer_latex:
            final_answer_latex = final_answer_latex.strip() or None
        alternate_solution_recommended = bool(
            getattr(solution_output, "alternate_solution_recommended", False)
        )
        alternate_solution_hint = getattr(
            solution_output, "alternate_solution_hint", None
        )
        if alternate_solution_hint:
            alternate_solution_hint = alternate_solution_hint.strip() or None
        if not alternate_solution_recommended:
            alternate_solution_hint = None

        # Combine problem + solution (strip any existing solution block from problem_latex)
        clean_problem = re.sub(
            r'\s*\\begin\{solution\}.*?\\end\{solution\}',
            '', problem_latex, flags=re.DOTALL,
        ).rstrip()
        clean_problem = re.sub(
            r'\s*\\begin\{finalanswer\}.*?\\end\{finalanswer\}',
            '', clean_problem, flags=re.DOTALL,
        ).rstrip()
        final_latex = clean_problem + "\n\n" + solution_latex

        # Mark answer in the combined LaTeX
        if answer_value:
            final_latex = self._mark_answer(final_latex, answer_type, answer_value, question_type)
        if answer_type == "subjective" and final_answer_latex:
            final_latex = self._append_subjective_answer(
                final_latex, final_answer_latex,
            )

        return SolutionResult(
            latex=final_latex,
            diagram_codes=diagram_codes,
            answer_type=answer_type,
            answer_value=answer_value,
            final_answer_latex=final_answer_latex,
            alternate_solution_recommended=alternate_solution_recommended,
            alternate_solution_hint=alternate_solution_hint,
            metadata={
                "subject": subject,
                "question_type": question_type,
                "answer_type": answer_type,
                "answer_value": answer_value,
                "final_answer_latex": final_answer_latex,
                "diagrams_requested": len(diagram_reqs),
                "diagrams_rendered": len(diagram_codes),
                "diagrams_assembled": assembled_count,
                "image_passed": has_diagram,
                "alternate_solution_decision_available": True,
                "alternate_solution_recommended": alternate_solution_recommended,
                "alternate_solution_hint": alternate_solution_hint,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_subject_agent(self, problem_latex, subject, question_type, chapter, topic, image_path=None):
        """Call the subject-specific solution agent."""
        from vbagent.agents.content_generation.solution import generate_solution

        return generate_solution(
            problem_text=problem_latex,
            question_type=question_type,
            subject=subject,
            chapter=chapter,
            topic=topic,
            image_path=image_path,
            show_spinner=True,
        )

    def _dispatch_diagrams(self, diagram_reqs, image_path, subject):
        """Dispatch diagram agents in parallel for each requirement.

        Passes diagram_type and rich context (values, labels, solution_context)
        from each DiagramRequirement to the TikZ router for better agent
        selection and generation quality.
        """
        from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
        from vbagent.models.classification import PrimaryClassification
        from vbagent.ui.logging import set_task_tag

        results: dict[str, str] = {}
        holders: dict[str, dict] = {}

        primary = PrimaryClassification(
            subject=subject,
            question_type="subjective",
            has_diagram=True,
            confidence=1.0,
            classified_from="latex",
        )

        def _gen(req):
            from vbagent.ui.logging import apply_agent_logging_context
            apply_agent_logging_context(self._logging_context)
            set_task_tag("SolnDiag")
            key = req.diagram_id if hasattr(req, "diagram_id") else f"diagram_{id(req)}"
            try:
                # Extract rich context from the requirement
                diagram_type = getattr(req, "diagram_type", None)
                context = getattr(req, "context", "") or ""
                values = getattr(req, "values", None)
                labels = getattr(req, "labels", None)

                code, agent_name = generate_tikz_with_routing(
                    image_path=image_path or None,
                    description=req.description,
                    diagram=None,
                    primary=primary,
                    use_context=True,
                    show_spinner=True,  # Show status like other agents
                    subject=subject,
                    diagram_type=diagram_type,
                    solution_context=context,
                    values=values if values else None,
                    labels=labels if labels else None,
                )
                holders[key] = {"code": code, "agent": agent_name, "error": None}
            except Exception as e:
                holders[key] = {"code": None, "agent": None, "error": str(e)}

        threads = []
        for req in diagram_reqs:
            t = threading.Thread(target=_gen, args=(req,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for key, h in holders.items():
            if h["code"]:
                results[key] = h["code"]
                self.console.print(f"[green]  OK {key}[/green] [dim](agent: {h['agent']})[/dim]")
            elif h["error"]:
                self.console.print(f"[yellow]  WARN {key} failed: {h['error']}[/yellow]")

        return results

    def _stitch_diagrams(
        self,
        solution_latex: str,
        diagram_codes: dict[str, str],
        diagram_requirements=None,
    ) -> str:
        """Replace diagram placeholders with actual TikZ code.

        Handles two placeholder formats:
          % DIAGRAM PLACEHOLDER: <id>
          % PLACEHOLDER: <id>
        Also replaces any surrounding empty tikzpicture wrapper.

        A diagram requirement and its generated TikZ are one unit.  If a
        subject agent forgets to emit the placeholder, do not silently drop
        the generated diagram: insert it before the closing solution
        environment (or append it if the environment is malformed).
        """
        requirements = {
            req.diagram_id: req
            for req in (diagram_requirements or [])
            if getattr(req, "diagram_id", None)
        }

        for diagram_id, tikz_code in diagram_codes.items():
            if not tikz_code or tikz_code.strip() in solution_latex:
                continue

            wrapped = (
                "\\begin{center}\n"
                + tikz_code.strip()
                + "\n\\end{center}"
            )

            # Format 1: % DIAGRAM PLACEHOLDER: <id>
            placeholder1 = f"% DIAGRAM PLACEHOLDER: {diagram_id}"
            if placeholder1 in solution_latex:
                solution_latex = solution_latex.replace(placeholder1, wrapped)
                continue

            # Format 2: % PLACEHOLDER: <id> (possibly inside a tikzpicture wrapper)
            placeholder2 = f"% PLACEHOLDER: {diagram_id}"
            if placeholder2 in solution_latex:
                # Remove surrounding empty tikzpicture + center if present
                pattern = (
                    r"\\begin\{center\}\s*"
                    r"\\begin\{tikzpicture\}\s*"
                    + re.escape(placeholder2)
                    + r"\s*\\end\{tikzpicture\}\s*"
                    r"\\end\{center\}"
                )
                if re.search(pattern, solution_latex):
                    solution_latex = re.sub(pattern, wrapped, solution_latex)
                else:
                    solution_latex = solution_latex.replace(placeholder2, wrapped)
                continue

            # The model requested a diagram but omitted its marker.  The
            # exact semantic location is unavailable in this case, so keep
            # the diagram inside the solution at the last safe location.
            # This is preferable to losing a successfully generated asset.
            solution_end = r"\end{solution}"
            insert_at = solution_latex.rfind(solution_end)
            fallback = (
                f"\n\n% Auto-inserted solution diagram: {diagram_id}\n"
                f"{wrapped}\n"
            )
            if insert_at >= 0:
                solution_latex = (
                    solution_latex[:insert_at]
                    + fallback
                    + solution_latex[insert_at:]
                )
                location = getattr(requirements.get(diagram_id), "location", "inline")
                self.console.print(
                    f"[yellow]  WARN {diagram_id}: placeholder missing; "
                    f"inserted diagram in solution ({location})[/yellow]"
                )
            else:
                solution_latex = solution_latex.rstrip() + fallback
                self.console.print(
                    f"[yellow]  WARN {diagram_id}: placeholder missing and "
                    "solution environment not found; appended diagram[/yellow]"
                )

        return solution_latex

    def _remove_diagram_placeholders(self, solution_latex: str) -> str:
        """Remove solution-diagram placeholders when diagram dispatch is disabled."""
        solution_latex = re.sub(
            r"%\s*(?:DIAGRAM\s+)?PLACEHOLDER:\s*[^\n]+",
            "",
            solution_latex,
        )
        # Remove wrappers left empty after the placeholder is removed, while
        # preserving centers that still contain real content.
        solution_latex = re.sub(
            r"\\begin\{center\}\s*\\end\{center\}",
            "",
            solution_latex,
        )
        solution_latex = re.sub(
            r"\\begin\{center\}\s*\\begin\{tikzpicture\}\s*"
            r"\\end\{tikzpicture\}\s*\\end\{center\}",
            "",
            solution_latex,
        )
        return solution_latex

    def _mark_answer(self, latex: str, answer_type: str, answer_value: str, question_type: str) -> str:
        r"""Insert answer marking into the LaTeX.

        MCQ: \ans after the correct option text (e.g. \task $5$ \ans)
        Integer: \hrulefill \ansint{N} at end of solution
        """
        if answer_type == "mcq" and answer_value:
            latex = self._mark_mcq_answer(latex, answer_value)
        elif answer_type == "integer" and answer_value:
            latex = self._mark_integer_answer(latex, answer_value)
        return latex

    def _mark_mcq_answer(self, latex: str, answer_value: str) -> str:
        r"""Mark the correct MCQ option with \ans.

        Finds the \task line for the correct option and appends \ans.
        Options are labeled (a), (b), (c), (d) or (A), (B), (C), (D).
        """
        # answer_value could be "b" or "B" or "a,c" for multiple correct
        options = [v.strip().lower() for v in answer_value.split(",")]
        option_index_map = {"a": 0, "b": 1, "c": 2, "d": 3}

        # Find all \task lines (MCQ options)
        task_pattern = re.compile(r"(\\task\b.*?)(\s*(?:\n|$))")
        matches = list(task_pattern.finditer(latex))

        if not matches:
            return latex

        # Mark correct options (work backwards to preserve indices)
        for opt_letter in reversed(sorted(options)):
            idx = option_index_map.get(opt_letter)
            if idx is not None and idx < len(matches):
                m = matches[idx]
                # Insert \ans after the task content, before the newline
                task_content = m.group(1).rstrip()
                trailing = m.group(2)
                if r"\ans" not in task_content:
                    replacement = task_content + " \\ans" + trailing
                    latex = latex[:m.start()] + replacement + latex[m.end():]

        return latex

    def _mark_integer_answer(self, latex: str, answer_value: str) -> str:
        r"""Mark integer answer with \hrulefill \ansint{N} before \end{solution}."""
        end_solution = r"\end{solution}"
        if end_solution in latex:
            insert = f"\n\n\\hrulefill \\ansint{{{answer_value}}}\n"
            latex = latex.replace(end_solution, insert + end_solution)
        return latex

    @staticmethod
    def _append_subjective_answer(latex: str, final_answer_latex: str) -> str:
        r"""Append a machine-readable subjective answer after the solution."""
        answer = final_answer_latex.strip()
        wrapped_match = re.fullmatch(
            r"\\begin\{finalanswer\}\s*(.*?)\s*\\end\{finalanswer\}",
            answer,
            flags=re.DOTALL,
        )
        if wrapped_match:
            answer = wrapped_match.group(1).strip()
        if not answer:
            return latex
        return (
            latex.rstrip()
            + "\n\n\\begin{finalanswer}\n"
            + answer
            + "\n\\end{finalanswer}"
        )


def create_solution_orchestrator(console=None) -> SolutionOrchestrator:
    """Factory function for SolutionOrchestrator."""
    return SolutionOrchestrator(console=console)
