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

    __slots__ = ("latex", "diagram_codes", "answer_type", "answer_value", "metadata")

    def __init__(
        self,
        latex: str,
        diagram_codes: dict[str, str] | None = None,
        answer_type: str = "subjective",
        answer_value: str | None = None,
        metadata: dict | None = None,
    ):
        self.latex = latex
        self.diagram_codes = diagram_codes or {}
        self.answer_type = answer_type
        self.answer_value = answer_value
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

    def run(
        self,
        problem_latex: str,
        subject: str,
        question_type: str,
        has_diagram: bool = False,
        image_path: Optional[str] = None,
    ) -> SolutionResult:
        """Generate a complete solution.

        Args:
            problem_latex: Scanned problem LaTeX from ProblemOrchestrator.
            subject: physics, chemistry, mathematics.
            question_type: mcq_sc, mcq_mc, subjective, etc.
            has_diagram: Whether the original problem has a diagram.
            image_path: Path to original image (passed to solver only if has_diagram).

        Returns:
            SolutionResult with final LaTeX including solution block.
        """
        # Step 1: Call subject agent
        self.console.print(f"[bold green]Generating {subject} solution...[/bold green]")
        solution_output = self._call_subject_agent(
            problem_latex, subject, question_type,
            image_path=image_path if has_diagram else None,
        )
        self.console.print("[green]✓[/green] Solution generated")

        solution_latex = solution_output.solution
        diagram_reqs = solution_output.diagram_requirements

        # Step 2: Dispatch diagram agents (parallel)
        diagram_codes: dict[str, str] = {}
        if diagram_reqs:
            self.console.print(f"[dim]  → Generating {len(diagram_reqs)} solution diagram(s)...[/dim]")
            diagram_codes = self._dispatch_diagrams(
                diagram_reqs, image_path, subject,
            )
            self.console.print(f"[green]  ✓ {len(diagram_codes)} diagram(s) rendered[/green]")

        # Step 3: Stitch diagrams into placeholders
        if diagram_codes:
            solution_latex = self._stitch_diagrams(solution_latex, diagram_codes)

        # Step 4: Answer marking
        answer_type = solution_output.answer_type
        answer_value = solution_output.answer_value

        # Combine problem + solution (strip any existing solution block from problem_latex)
        clean_problem = re.sub(
            r'\s*\\begin\{solution\}.*?\\end\{solution\}',
            '', problem_latex, flags=re.DOTALL,
        ).rstrip()
        final_latex = clean_problem + "\n\n" + solution_latex

        # Mark answer in the combined LaTeX
        if answer_value:
            final_latex = self._mark_answer(final_latex, answer_type, answer_value, question_type)

        return SolutionResult(
            latex=final_latex,
            diagram_codes=diagram_codes,
            answer_type=answer_type,
            answer_value=answer_value,
            metadata={
                "subject": subject,
                "question_type": question_type,
                "diagrams_requested": len(diagram_reqs),
                "diagrams_rendered": len(diagram_codes),
                "image_passed": has_diagram,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_subject_agent(self, problem_latex, subject, question_type, image_path=None):
        """Call the subject-specific solution agent."""
        from vbagent.agents.content_generation.solution import generate_solution

        return generate_solution(
            problem_text=problem_latex,
            question_type=question_type,
            subject=subject,
            image_path=image_path,
            show_spinner=True,
        )

    def _dispatch_diagrams(self, diagram_reqs, image_path, subject):
        """Dispatch diagram agents in parallel for each requirement."""
        from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
        from vbagent.models.classification import PrimaryClassification

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
            key = req.diagram_id if hasattr(req, "diagram_id") else f"diagram_{id(req)}"
            try:
                code, agent_name = generate_tikz_with_routing(
                    image_path=image_path or "",
                    description=req.description,
                    diagram=None,
                    primary=primary,
                    use_context=True,
                    show_spinner=False,
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
            elif h["error"]:
                self.console.print(f"[yellow]  ⚠ Diagram {key} failed: {h['error']}[/yellow]")

        return results

    def _stitch_diagrams(self, solution_latex: str, diagram_codes: dict[str, str]) -> str:
        """Replace % DIAGRAM PLACEHOLDER: <id> with actual TikZ code."""
        for diagram_id, tikz_code in diagram_codes.items():
            placeholder = f"% DIAGRAM PLACEHOLDER: {diagram_id}"
            replacement = (
                "\\begin{center}\n"
                + tikz_code.strip()
                + "\n\\end{center}"
            )
            solution_latex = solution_latex.replace(placeholder, replacement)
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


def create_solution_orchestrator(console=None) -> SolutionOrchestrator:
    """Factory function for SolutionOrchestrator."""
    return SolutionOrchestrator(console=console)
