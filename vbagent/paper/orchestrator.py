"""PaperOrchestrator — main coordinator for paper generation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from vbagent.tex import format_tex

from .generator import ProblemGenerator
from .manifest import PaperManifest
from .models import (
    CoverageReport,
    GeneratedProblemResult,
    GenerationReport,
    GenerationTarget,
    HintReport,
    HintResult,
    PaperState,
    PostGenClassification,
    ProblemEntry,
    SolutionReport,
)
from .qa import QAPipeline
from .syllabus import SyllabusManager


class PaperOrchestrator:
    """Top-level coordinator for paper generation workflows."""

    def __init__(
        self,
        base_dir: Path = Path("agentic"),
        config=None,
        console=None,
    ):
        if config is None:
            from vbagent.config import get_config
            config = get_config()
        if console is None:
            from vbagent.cli.common import _get_console
            console = _get_console()

        self.base_dir = Path(base_dir)
        self.config = config
        self.console = console
        self.manifest = PaperManifest(self.base_dir)
        self.generator = ProblemGenerator(config, console)
        self.qa_pipeline = QAPipeline(config, console)
        self.syllabus_mgr = SyllabusManager()

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def init_paper(
        self,
        source_dir: Optional[Path],
        subject: str,
        target_counts: Optional[dict[str, int]] = None,
        force: bool = False,
    ) -> PaperState:
        if self.manifest.exists() and not force:
            return self.manifest.load()

        state = self.manifest.load()
        state.subject = subject
        state.base_dir = str(self.base_dir)

        # Resolve source: explicit --from-problems, or auto-discover scans/ inside paper dir
        resolved_source = Path(source_dir) if source_dir else None
        if resolved_source is None:
            scans_dir = self.base_dir / "scans"
            if scans_dir.exists() and any(scans_dir.glob("Problem_*.tex")):
                resolved_source = scans_dir
                self.console.print(f"[dim]Auto-discovered {resolved_source}[/dim]")

        if resolved_source:
            tex_files = sorted(resolved_source.glob("*.tex"))
            if tex_files:
                syllabus = self.syllabus_mgr.extract_from_problems(tex_files, subject)
                if target_counts:
                    for topic in syllabus.topics:
                        if topic.name in target_counts:
                            topic.target_count = target_counts[topic.name]
                    syllabus.total_target = sum(t.target_count for t in syllabus.topics)

                syllabus_path = self.base_dir / "syllabus.json"
                self.syllabus_mgr.save(syllabus_path)

                # Extract serial from filename (Problem_N.tex) or assign sequentially
                import re
                serial_pattern = re.compile(r"Problem_(\d+)\.tex$", re.IGNORECASE)
                for f in tex_files:
                    m = serial_pattern.match(f.name)
                    serial = int(m.group(1)) if m else self.manifest.get_next_serial(state)
                    # Skip if serial already registered
                    if any(p.serial == serial for p in state.problems):
                        continue
                    state.problems.append(ProblemEntry(
                        serial=serial, filename=f.name, subject=subject,
                        topic="uncategorized", source="scanned",
                    ))

        self.manifest.save(state)
        return state

    # ------------------------------------------------------------------
    # Standalone generation
    # ------------------------------------------------------------------

    def generate_standalone(
        self,
        topic: str,
        question_type: str = "subjective",
        difficulty: str = "medium",
        concepts: Optional[list[str]] = None,
        idea: Optional[str] = None,
        with_solution: bool = True,
        tone: str = "",
        with_diagram: bool = True,
    ) -> GeneratedProblemResult:
        state = self.manifest.load()
        # Use explicit tone arg, fall back to paper-level tone
        effective_tone = tone or state.tone

        # Collect already-covered subtopics for diversity
        covered = self._covered_subtopics(state, topic)

        target = GenerationTarget(
            topic=topic, difficulty=difficulty, question_type=question_type,
            concepts=concepts or [], strategy="idea_generator",
            seed_ideas=[idea] if idea else [],
        )

        self.console.print(f"[bold green]Generating {topic} {question_type}...[/bold green]")
        result = self.generator.generate(
            target, with_solution=with_solution, tone=effective_tone,
            avoid_subtopics=covered,
        )

        serial = self.manifest.get_next_serial(state)
        filename = f"Problem_{serial}.tex"

        # Auto-diagram: if idea generator provided a diagram description, generate TikZ
        diagram_desc = result.diagram_description
        diagram_status = "none"
        if with_diagram and diagram_desc:
            subject = state.subject or self.config.subject
            tikz_code = self._generate_diagram(diagram_desc, subject, result.problem_tex)
            if tikz_code:
                result = self._inject_tikz(result, tikz_code)
                diagram_status = "generated"

        self._save_problem(result.combined_tex, filename)

        entry = ProblemEntry(
            serial=serial, filename=filename, subject=self.config.subject,
            topic=topic, difficulty=difficulty, question_type=question_type,
            concepts=concepts or [], source="generated",
            solution_status="inline" if with_solution else "none",
            diagram_status=diagram_status,
            diagram_description=diagram_desc,
        )

        # Cache problem
        self._cache_content(f"paper_{serial}", "scan", result.combined_tex)

        # Post-generation classification — enrich subtopic, concepts, difficulty
        classification = self._classify_generated(result.problem_tex, state.subject or self.config.subject, topic)
        if classification:
            entry.subtopic = classification.subtopic or entry.subtopic
            entry.concepts = classification.concepts or entry.concepts
            entry.difficulty = classification.difficulty or entry.difficulty
            self.console.print(f"[dim]  ↳ classified: {entry.subtopic} | {entry.concepts}[/dim]")

        self.manifest.add_problem(state, entry)
        self.console.print(f"[green]✓[/green] {filename} generated")
        return result

    # ------------------------------------------------------------------
    # Syllabus-driven generation
    # ------------------------------------------------------------------

    def generate_problems(
        self,
        count: int = 1,
        take_idea_from: Optional[list[int]] = None,
        with_solution: bool = True,
    ) -> GenerationReport:
        state = self.manifest.load()
        self._load_syllabus()

        coverage_before = self.syllabus_mgr.analyze_coverage(state.problems).overall_coverage_pct
        generated: list[ProblemEntry] = []

        for _ in range(count):
            coverage = self.syllabus_mgr.analyze_coverage(state.problems)
            if coverage.overall_coverage_pct >= 100.0:
                break

            target = self.syllabus_mgr.select_next_target(coverage)

            seed_problems = None
            if take_idea_from:
                seed_problems = [
                    self._load_problem_tex(s, state) for s in take_idea_from
                    if any(p.serial == s for p in state.problems)
                ]
                if len(seed_problems) == 1:
                    target.strategy = "cross_topic"
                elif len(seed_problems) >= 2:
                    target.strategy = "combiner"

            self.console.print(f"[dim]  → Generating {target.topic} ({target.difficulty})...[/dim]")
            result = self.generator.generate(
                target, seed_problems, with_solution, tone=state.tone,
                avoid_subtopics=self._covered_subtopics(state, target.topic),
            )

            qa_result = self.qa_pipeline.run(result.problem_tex, result.solution_tex)
            final_tex = qa_result.fixed_tex if (not qa_result.passed and qa_result.fixed_tex) else result.combined_tex

            # Auto-diagram if idea generator provided description
            diagram_desc = result.diagram_description
            diagram_status = "none"
            if diagram_desc:
                tikz_code = self._generate_diagram(diagram_desc, state.subject, result.problem_tex)
                if tikz_code:
                    # Inject into final_tex
                    final_tex = final_tex + "\n\n" + tikz_code
                    diagram_status = "generated"

            serial = self.manifest.get_next_serial(state)
            filename = f"Problem_{serial}.tex"
            self._save_problem(final_tex, filename)

            entry = ProblemEntry(
                serial=serial, filename=filename, subject=state.subject,
                topic=target.topic, subtopic=target.subtopic,
                difficulty=target.difficulty, question_type=target.question_type,
                concepts=target.concepts,
                source="seeded" if take_idea_from else "generated",
                seed_from=take_idea_from or [],
                qa_status="passed" if qa_result.passed else "failed",
                solution_status="inline" if with_solution else "none",
                diagram_status=diagram_status,
                diagram_description=diagram_desc,
            )

            # Post-generation classification
            classification = self._classify_generated(result.problem_tex, state.subject, target.topic)
            if classification:
                entry.subtopic = classification.subtopic or entry.subtopic
                entry.concepts = classification.concepts or entry.concepts
                entry.difficulty = classification.difficulty or entry.difficulty

            state.problems.append(entry)
            self.manifest.save(state)
            self.syllabus_mgr.update_after_generation(entry)
            generated.append(entry)
            self.console.print(f"[green]  ✓ {filename}[/green]")

        coverage_after = self.syllabus_mgr.analyze_coverage(state.problems).overall_coverage_pct
        return GenerationReport(
            total_requested=count, total_generated=len(generated),
            total_passed_qa=sum(1 for p in generated if p.qa_status == "passed"),
            problems=generated, coverage_before=coverage_before,
            coverage_after=coverage_after,
        )

    def generate_batch(
        self, per_topic: dict[str, int], with_solution: bool = True,
    ) -> GenerationReport:
        all_generated: list[ProblemEntry] = []
        for topic, count in per_topic.items():
            for _ in range(count):
                result = self.generate_standalone(
                    topic=topic, with_solution=with_solution,
                )
                state = self.manifest.load()
                if state.problems:
                    all_generated.append(state.problems[-1])
        return GenerationReport(
            total_requested=sum(per_topic.values()),
            total_generated=len(all_generated), problems=all_generated,
        )

    # ------------------------------------------------------------------
    # Solution generation (independent)
    # ------------------------------------------------------------------

    def generate_solutions(self, problem_ids: Optional[list[int]] = None) -> SolutionReport:
        state = self.manifest.load()
        targets = [p for p in state.problems if p.serial in problem_ids] if problem_ids else [
            p for p in state.problems if p.solution_status in ("none", "inline")
        ]

        results = []
        for entry in targets:
            try:
                problem_latex = self._load_problem_tex(entry.serial, state)
                from vbagent.agents.orchestration.solution_orchestrator import SolutionOrchestrator
                solver = SolutionOrchestrator(console=self.console)
                sol = solver.run(
                    problem_latex=problem_latex, subject=entry.subject,
                    question_type=entry.question_type,
                )
                # Extract just the solution block (not the duplicated problem)
                sol_block = self._extract_env_block(sol.latex, "solution")
                if not sol_block:
                    sol_block = sol.latex  # fallback: use full output

                # Save standalone copy in solutions/
                sol_path = self.base_dir / "solutions" / entry.filename
                sol_path.parent.mkdir(parents=True, exist_ok=True)
                sol_path.write_text(format_tex(sol_block), encoding="utf-8")

                # Stitch into the problem file in scans/
                self._stitch_into_problem(entry, sol_block)

                entry.solution_status = "generated"
                self._cache_content(f"paper_{entry.serial}", "solution", sol_block)
                results.append({"serial": entry.serial, "success": True})
                self.console.print(f"[green]  ✓ Solution for {entry.filename}[/green]")
            except Exception as e:
                results.append({"serial": entry.serial, "success": False, "error": str(e)})
                self.console.print(f"[yellow]  ⚠ Solution failed for {entry.filename}: {e}[/yellow]")

        self.manifest.save(state)
        return SolutionReport(
            total=len(targets), solved=sum(1 for r in results if r.get("success")),
            failed=sum(1 for r in results if not r.get("success")), results=results,
        )

    # ------------------------------------------------------------------
    # Hint generation
    # ------------------------------------------------------------------

    def generate_hints(
        self, problem_ids: Optional[list[int]] = None, hint_style: str = "conceptual",
    ) -> HintReport:
        state = self.manifest.load()
        targets = [p for p in state.problems if p.serial in problem_ids] if problem_ids else [
            p for p in state.problems if p.hint_status == "none"
        ]

        results = []
        for entry in targets:
            try:
                problem_latex = self._load_problem_tex(entry.serial, state)
                solution_latex = self._load_solution_tex(entry)
                hint = self._generate_hint(
                    problem_latex, solution_latex, entry.subject, entry.topic, hint_style,
                )
                hint_path = self.base_dir / "hints" / entry.filename
                hint_path.parent.mkdir(parents=True, exist_ok=True)
                hint_path.write_text(hint.hint_text, encoding="utf-8")
                entry.hint_status = "generated"

                # Wrap in \begin{hint}...\end{hint} and stitch into problem file
                hint_block = f"\\begin{{hint}}\n{hint.hint_text.strip()}\n\\end{{hint}}"
                self._stitch_into_problem(entry, hint_block)

                # Cache hint
                self._cache_content(f"paper_{entry.serial}", "hint", hint.hint_text)
                results.append({"serial": entry.serial, "hint_text": hint.hint_text, "success": True})
                self.console.print(f"[green]  ✓ Hint for {entry.filename}[/green]")
            except Exception as e:
                results.append({"serial": entry.serial, "success": False, "error": str(e)})

        self.manifest.save(state)
        return HintReport(
            total=len(targets), generated=sum(1 for r in results if r.get("success")),
            failed=sum(1 for r in results if not r.get("success")), results=results,
        )

    def _generate_hint(self, problem_latex, solution_latex, subject, topic, hint_style):
        from vbagent.agents.base import create_agent, run_agent_sync

        styles = {
            "conceptual": "Ask a guiding question that points toward the right reasoning. Do NOT state the answer. Example: 'Is heat escaping? If not, conservative force means what for energy?'",
            "equation": "Provide ONE key equation central to solving this, without showing how to apply it. Example: '$W_{\\text{net}} = \\Delta KE$'",
            "direction": "Give a one-sentence approach pointer. Example: 'Resolve forces along the incline, then apply Newton\\'s second law.'",
        }
        prompt = f"""You are an expert {subject} educator. Generate a SHORT hint.
Style: {hint_style}
Instructions: {styles.get(hint_style, styles["conceptual"])}
RULES: Max 2 sentences or 1 equation + 1 sentence. Do NOT reveal the answer.
Respond with JSON: {{"hint_text": "...", "hint_style": "{hint_style}", "key_concept": "..."}}"""

        agent = create_agent(
            name=f"HintGenerator-{subject}", instructions=prompt,
            output_type=HintResult, agent_type="variant",
        )
        context = f"Problem:\n```latex\n{problem_latex}\n```"
        if solution_latex:
            context += f"\n\nSolution (reference only, do NOT reveal):\n```latex\n{solution_latex}\n```"
        context += f"\nTopic: {topic}\nGenerate a {hint_style} hint."
        return run_agent_sync(agent, context)

    # ------------------------------------------------------------------
    # Status & QA
    # ------------------------------------------------------------------

    def get_status(self) -> PaperState:
        return self.manifest.load()

    def run_qa(self, problem_ids: Optional[list[int]] = None) -> list[dict]:
        state = self.manifest.load()
        targets = [p for p in state.problems if p.serial in problem_ids] if problem_ids else state.problems
        results = []
        for entry in targets:
            tex = self._load_problem_tex(entry.serial, state)
            qa = self.qa_pipeline.run(tex)
            entry.qa_status = "passed" if qa.passed else "failed"
            results.append({"serial": entry.serial, "passed": qa.passed, "issues": [c.issues for c in qa.checks]})
        self.manifest.save(state)
        return results

    # ------------------------------------------------------------------
    # Diagram generation
    # ------------------------------------------------------------------

    def _generate_diagram(self, description: str, subject: str, problem_tex: str) -> Optional[str]:
        """Generate TikZ code from a text description using the existing diagram router."""
        try:
            from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing

            self.console.print(f"[dim]  ↳ generating diagram: {description[:60]}...[/dim]")
            tikz_code, agent_type = generate_tikz_with_routing(
                description=description,
                subject=subject,
                problem_text=problem_tex,
            )
            self.console.print(f"[dim]  ↳ diagram agent: {agent_type}[/dim]")
            return tikz_code
        except Exception as e:
            self.console.print(f"[dim yellow]  ⚠ diagram generation skipped: {e}[/dim yellow]")
            return None

    def _inject_tikz(self, result: GeneratedProblemResult, tikz_code: str) -> GeneratedProblemResult:
        """Inject TikZ code into the problem tex, before the solution if present."""
        # Place diagram after the problem statement, before solution
        if result.solution_tex and result.solution_tex in result.combined_tex:
            combined = result.combined_tex.replace(
                result.solution_tex,
                "\n\n" + tikz_code + "\n\n" + result.solution_tex,
            )
        else:
            combined = result.problem_tex + "\n\n" + tikz_code
            if result.solution_tex:
                combined += "\n\n" + result.solution_tex

        return GeneratedProblemResult(
            problem_tex=result.problem_tex + "\n\n" + tikz_code,
            solution_tex=result.solution_tex,
            combined_tex=combined,
            target=result.target,
            strategy_used=result.strategy_used,
            diagram_description=result.diagram_description,
        )

    def generate_diagrams(self, problem_ids: Optional[list[int]] = None, description: Optional[str] = None) -> list[dict]:
        """Add diagrams to existing problems.

        If description is provided, uses it for all targeted problems.
        Otherwise, uses each problem's stored diagram_description, or
        asks a lightweight LLM to decide if a diagram is needed and describe it.
        """
        state = self.manifest.load()
        targets = (
            [p for p in state.problems if p.serial in problem_ids]
            if problem_ids
            else [p for p in state.problems if p.diagram_status == "none"]
        )

        results = []
        for entry in targets:
            try:
                tex = self._load_problem_tex(entry.serial, state)
                desc = description or entry.diagram_description

                # If no description stored, ask LLM whether this problem needs a diagram
                if not desc:
                    desc = self._assess_diagram_need(tex, entry.subject or state.subject, entry.topic)
                    if not desc:
                        results.append({"serial": entry.serial, "success": False, "reason": "no diagram needed"})
                        self.console.print(f"[dim]  #{entry.serial} — no diagram needed[/dim]")
                        continue

                tikz_code = self._generate_diagram(desc, entry.subject or state.subject, tex)
                if tikz_code:
                    # Save diagram as separate file and also append to problem
                    diag_dir = self.base_dir / "diagrams"
                    diag_dir.mkdir(parents=True, exist_ok=True)
                    diag_path = diag_dir / entry.filename
                    diag_path.write_text(tikz_code, encoding="utf-8")

                    # Append TikZ to the problem file
                    problem_path = self.base_dir / "scans" / entry.filename
                    current_tex = problem_path.read_text(encoding="utf-8")
                    problem_path.write_text(format_tex(current_tex + "\n\n" + tikz_code), encoding="utf-8")

                    entry.diagram_status = "generated"
                    entry.diagram_description = desc
                    results.append({"serial": entry.serial, "success": True, "description": desc})
                    self.console.print(f"[green]  ✓ #{entry.serial}[/green] diagram added")
                else:
                    results.append({"serial": entry.serial, "success": False, "reason": "generation failed"})
            except Exception as e:
                results.append({"serial": entry.serial, "success": False, "error": str(e)})
                self.console.print(f"[yellow]  ⚠ #{entry.serial} failed: {e}[/yellow]")

        self.manifest.save(state)
        return results

    def _assess_diagram_need(self, problem_tex: str, subject: str, topic: str) -> Optional[str]:
        """Lightweight LLM call to decide if a problem needs a diagram and describe it."""
        try:
            from vbagent.agents.base import create_agent, run_agent_sync

            prompt = f"""You are a {subject} exam expert. Given a LaTeX problem, decide if it would benefit from a diagram.
If YES, respond with JSON: {{"needs_diagram": true, "description": "<detailed description of the diagram>"}}
If NO, respond with JSON: {{"needs_diagram": false, "description": ""}}

The description should be specific enough for a TikZ agent to draw it.
Examples of good descriptions:
- "Free body diagram of a block on a 30-degree inclined plane with friction, normal force, weight, and applied force vectors"
- "Velocity-time graph showing three phases: linear increase 0-6s, constant 6-16s, linear decrease 16-20s"
- "Projectile trajectory parabola from origin to range R, with point P marked at (20,10)"
"""
            from pydantic import BaseModel as _BM

            class _DiagramNeed(_BM):
                needs_diagram: bool = False
                description: str = ""

            agent = create_agent(
                name=f"DiagramAssessor-{subject}",
                instructions=prompt,
                output_type=_DiagramNeed,
                agent_type="classifier",
            )
            context = f"Topic: {topic}\n\nProblem:\n```latex\n{problem_tex[:3000]}\n```"
            result = run_agent_sync(agent, context, show_spinner=False)
            if result.needs_diagram and result.description:
                return result.description
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Post-generation classification
    # ------------------------------------------------------------------

    def _classify_generated(self, problem_tex: str, subject: str, topic: str) -> Optional[PostGenClassification]:
        """Lightweight LLM call to extract subtopic, concepts, difficulty from generated LaTeX."""
        try:
            from vbagent.agents.base import create_agent, run_agent_sync

            prompt = f"""You are a {subject} exam expert. Given a LaTeX problem, extract:
- subtopic: specific subtopic (e.g. "Lagrangian mechanics", "projectile motion", "SN2 reactions")
- concepts: list of 2-5 key concepts tested (e.g. ["conservation of energy", "moment of inertia"])
- difficulty: one of easy, medium, hard
- question_type: one of subjective, mcq_sc, mcq_mc, assertion_reason, passage, integer, matrix_match
- brief_description: one-sentence summary of what the problem asks

Be precise and specific. The subtopic should be narrower than the topic "{topic}"."""

            agent = create_agent(
                name=f"PostGenClassifier-{subject}",
                instructions=prompt,
                output_type=PostGenClassification,
                agent_type="classifier",
            )
            context = f"Topic: {topic}\n\nProblem LaTeX:\n```latex\n{problem_tex[:3000]}\n```"
            return run_agent_sync(agent, context, show_spinner=False)
        except Exception as e:
            self.console.print(f"[dim yellow]  ⚠ classification skipped: {e}[/dim yellow]")
            return None

    def _covered_subtopics(self, state: PaperState, topic: str) -> list[str]:
        """Collect subtopics already generated for a given topic."""
        return list({
            p.subtopic for p in state.problems
            if p.topic == topic and p.subtopic
        })

    def enrich_problems(self, problem_ids: Optional[list[int]] = None) -> list[dict]:
        """Batch retroactive classification for problems with empty subtopics."""
        state = self.manifest.load()
        targets = (
            [p for p in state.problems if p.serial in problem_ids]
            if problem_ids
            else [p for p in state.problems if not p.subtopic]
        )

        results = []
        for entry in targets:
            try:
                tex = self._load_problem_tex(entry.serial, state)
                classification = self._classify_generated(tex, entry.subject or state.subject, entry.topic)
                if classification:
                    entry.subtopic = classification.subtopic or entry.subtopic
                    entry.concepts = classification.concepts or entry.concepts
                    entry.difficulty = classification.difficulty or entry.difficulty
                    results.append({"serial": entry.serial, "subtopic": entry.subtopic, "concepts": entry.concepts, "success": True})
                    self.console.print(f"[green]  ✓ #{entry.serial}[/green] → {entry.subtopic} | {entry.concepts}")
                else:
                    results.append({"serial": entry.serial, "success": False, "error": "classification returned None"})
            except Exception as e:
                results.append({"serial": entry.serial, "success": False, "error": str(e)})
                self.console.print(f"[yellow]  ⚠ #{entry.serial} failed: {e}[/yellow]")

        self.manifest.save(state)
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Compile
    # ------------------------------------------------------------------

    def compile_paper(
        self,
        output: str = "main.tex",
        title: Optional[str] = None,
        all_packages: bool = False,
        run_pdflatex: bool = False,
        problems: Optional[list[int]] = None,
        inline: bool = False,
        only: Optional[str] = None,
    ) -> dict:
        """Assemble main.tex from manifest and optionally compile to PDF.

        Args:
            only: Filter content — "hints", "solutions", "problems", or None (all).

        Returns dict with keys: output_path, packages_log, pdf_path (if compiled),
        success, problem_count.
        """
        import re
        import subprocess

        from vbagent.cli.compilation.compile_main import generate_preamble

        state = self.manifest.load()
        if not state.problems:
            raise ValueError("No problems in manifest — nothing to compile")

        # Filter problems if requested
        entries = state.problems
        if problems:
            entries = [p for p in entries if p.serial in problems]
            if not entries:
                raise ValueError(f"None of the requested serials {problems} found in manifest")

        scans_dir = self.base_dir / "scans"
        subject = state.subject
        paper_title = title or f"{subject.title()} Paper — {state.paper_id}"

        # --- Package detection: scan .tex files for special environments ---
        package_reasons: list[str] = []
        detected_envs: set[str] = set()

        for entry in entries:
            tex_path = scans_dir / entry.filename
            if not tex_path.exists():
                continue
            content = tex_path.read_text(encoding="utf-8")
            if r"\begin{tikzpicture}" in content:
                detected_envs.add("tikzpicture")
            if r"\begin{circuitikz}" in content:
                detected_envs.add("circuitikz")
            if r"\chemfig" in content:
                detected_envs.add("chemfig")
            if r"\ce{" in content:
                detected_envs.add("mhchem")
            if r"\begin{pgfplot" in content or r"\begin{axis}" in content:
                detected_envs.add("pgfplots")
            if r"\begin{venndiagram" in content:
                detected_envs.add("venndiagram")

        # Log package decisions
        subject_pkg_map = {
            "physics": ["circuitikz", "kinematikz", "tzplot", "pgfplots"],
            "chemistry": ["chemfig", "mhchem", "chemmacros", "pgfplots"],
            "mathematics": ["pgfplots", "tkz-euclide", "venndiagram"],
        }
        env_to_pkg = {
            "tikzpicture": "tikz (base)",
            "circuitikz": "circuitikz",
            "chemfig": "chemfig",
            "mhchem": "mhchem",
            "pgfplots": "pgfplots",
            "venndiagram": "venndiagram",
        }

        self.console.print(f"\n[bold]Assembling main.tex[/bold]")
        self.console.print(f"  Subject: {subject}")
        self.console.print(f"  Problems: {len(entries)}")

        # Subject packages
        subj_pkgs = subject_pkg_map.get(subject, [])
        if all_packages:
            package_reasons.append("--all-packages: including all subject packages")
            self.console.print(f"  [cyan]Packages:[/cyan] ALL (--all-packages)")
        else:
            package_reasons.append(f"Subject '{subject}': {', '.join(subj_pkgs)}")
            self.console.print(f"  [cyan]Packages ({subject}):[/cyan] {', '.join(subj_pkgs)}")

        # Detected environments
        if detected_envs:
            for env in sorted(detected_envs):
                pkg = env_to_pkg.get(env, env)
                reason = f"Detected \\begin{{{env}}} in problem files → {pkg}"
                package_reasons.append(reason)
                self.console.print(f"  [dim]  ↳ {reason}[/dim]")

        # Diagram count
        diag_count = sum(1 for e in entries if e.diagram_status != "none")
        if diag_count:
            package_reasons.append(f"{diag_count} problem(s) have diagrams")
            self.console.print(f"  [dim]  ↳ {diag_count} problem(s) with diagrams[/dim]")

        # Global tikzset
        package_reasons.append("Global \\tikzset: >=latex, thick, every node font=\\small")
        self.console.print(f"  [dim]  ↳ Global \\tikzset: >=latex, thick, every node font=\\small[/dim]")

        # --- Generate preamble ---
        preamble = generate_preamble(subject=subject, title=paper_title, include_all=all_packages)

        # --- Assemble: stitch solutions/hints into scans/ files ---
        assembled = self._assemble_problems(entries)
        if assembled:
            self.console.print(f"  [dim]  ↳ assembled solutions/hints into {assembled} problem file(s)[/dim]")

        # --- Build document body ---
        body_lines = [
            r"\begin{document}",
            r"\maketitle",
        ]

        # Determine which environments to include
        include_problem = only in (None, "problems")
        include_solution = only in (None, "solutions")
        include_hint = only in (None, "hints")

        if only:
            self.console.print(f"  [dim]  ↳ --only {only}[/dim]")

        if only is None and not inline:
            # Default: full content via \input
            body_lines.append(r"\begin{enumerate}")
            for entry in sorted(entries, key=lambda e: e.serial):
                body_lines.append(f"\\input{{scans/{entry.filename}}}")
            body_lines.append(r"\end{enumerate}")
        else:
            # Filtered or inline: extract specific environments per problem
            body_lines.append(r"\begin{enumerate}")

            for entry in sorted(entries, key=lambda e: e.serial):
                tex_path = scans_dir / entry.filename
                if not tex_path.exists():
                    continue
                full_content = tex_path.read_text(encoding="utf-8")

                # Detect passage-type problem (has \textsc{Comprehensive Passage})
                is_passage = r"\textsc{Comprehensive Passage}" in full_content

                parts: list[str] = []
                if include_problem:
                    # Everything before the first \begin{solution/hint/alternatesolution/idea/remark}
                    import re as _re
                    problem_part = _re.split(
                        r'\s*\\begin\{(?:solution|alternatesolution|hint|idea|remark)\}',
                        full_content, maxsplit=1,
                    )[0].strip()
                    parts.append(problem_part)

                if include_solution:
                    sol_block = self._extract_env_block(full_content, "solution")
                    if sol_block:
                        if not include_problem:
                            if is_passage:
                                # For passage: include header + empty sub-items for counter
                                parts.append(self._passage_skeleton(full_content))
                            else:
                                parts.append(f"\\item[]")  # empty item for numbering
                        parts.append(sol_block)
                    alt_block = self._extract_env_block(full_content, "alternatesolution")
                    if alt_block:
                        parts.append(alt_block)
                    idea_block = self._extract_env_block(full_content, "idea")
                    if idea_block:
                        parts.append(idea_block)
                    remark_block = self._extract_env_block(full_content, "remark")
                    if remark_block:
                        parts.append(remark_block)

                if include_hint:
                    hint_block = self._extract_env_block(full_content, "hint")
                    if hint_block:
                        if not include_problem and not include_solution:
                            if is_passage:
                                parts.append(self._passage_skeleton(full_content))
                            else:
                                parts.append(f"\\item[]")  # empty item for numbering
                        parts.append(hint_block)

                if parts:
                    body_lines.append(f"% --- Problem {entry.serial} ---")
                    body_lines.append("\n".join(parts))
                    body_lines.append("")

            body_lines.append(r"\end{enumerate}")

        body_lines.append(r"\end{document}")

        content = preamble + "\n" + "\n".join(body_lines) + "\n"

        # --- Write main.tex ---
        output_path = self.base_dir / output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        self.console.print(f"\n[green]✓[/green] Written {output_path}")

        result = {
            "output_path": str(output_path),
            "packages_log": package_reasons,
            "problem_count": len(entries),
            "success": True,
            "pdf_path": None,
        }

        # --- Optionally run pdflatex ---
        if run_pdflatex:
            self.console.print(f"\n[cyan]Running pdflatex...[/cyan]")
            try:
                proc = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", output],
                    cwd=str(self.base_dir),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                pdf_name = output.replace(".tex", ".pdf")
                pdf_path = self.base_dir / pdf_name
                if pdf_path.exists():
                    size_kb = pdf_path.stat().st_size / 1024
                    self.console.print(f"[green]✓[/green] PDF generated: {pdf_path} ({size_kb:.0f} KB)")
                    result["pdf_path"] = str(pdf_path)
                else:
                    self.console.print(f"[red]✗[/red] pdflatex finished but no PDF produced")
                    if proc.stdout:
                        # Show last 15 lines of log for debugging
                        log_lines = proc.stdout.strip().split("\n")
                        for line in log_lines[-15:]:
                            self.console.print(f"  [dim]{line}[/dim]")
                    result["success"] = False
            except FileNotFoundError:
                self.console.print("[red]✗[/red] pdflatex not found — install TeX Live or MiKTeX")
                result["success"] = False
            except subprocess.TimeoutExpired:
                self.console.print("[red]✗[/red] pdflatex timed out (120s)")
                result["success"] = False

        return result

    def _save_problem(self, tex: str, filename: str) -> Path:
        scans_dir = self.base_dir / "scans"
        scans_dir.mkdir(parents=True, exist_ok=True)
        path = scans_dir / filename
        path.write_text(format_tex(tex), encoding="utf-8")
        return path

    def _load_problem_tex(self, serial: int, state: PaperState) -> str:
        entry = next((p for p in state.problems if p.serial == serial), None)
        if not entry:
            raise FileNotFoundError(f"Problem {serial} not in manifest")
        path = self.base_dir / "scans" / entry.filename
        return path.read_text(encoding="utf-8")

    def _load_solution_tex(self, entry: ProblemEntry) -> Optional[str]:
        path = self.base_dir / "solutions" / entry.filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def _cache_content(self, problem_id: str, stage: str, content: str) -> None:
        """Cache content (solution, hint, etc.) via PipelineCache."""
        try:
            from vbagent.cache import PipelineCache
            cache = PipelineCache(base_dir=str(self.base_dir))
            cache.set(problem_id, stage, content)
        except Exception:
            pass  # caching is best-effort

    def _stitch_into_problem(self, entry: ProblemEntry, block: str) -> None:
        """Append a LaTeX block (solution, hint, etc.) into the problem file in scans/.

        Avoids duplicating if the same environment is already present.
        """
        import re
        path = self.base_dir / "scans" / entry.filename
        if not path.exists():
            return
        current = path.read_text(encoding="utf-8")

        # Detect environment name from block (e.g. "solution", "hint", "alternatesolution")
        env_match = re.match(r'\\begin\{(\w+)\}', block.strip())
        if env_match:
            env_name = env_match.group(1)
            # Skip if this environment already exists in the file
            if f"\\begin{{{env_name}}}" in current:
                return

        updated = current.rstrip() + "\n\n" + block.strip() + "\n"
        path.write_text(format_tex(updated), encoding="utf-8")

    @staticmethod
    def _extract_env_block(latex: str, env_name: str) -> Optional[str]:
        """Extract \\begin{env}...\\end{env} block from LaTeX string."""
        import re
        pattern = re.compile(
            rf'(\\begin\{{{env_name}\}}.*?\\end\{{{env_name}\}})',
            re.DOTALL,
        )
        m = pattern.search(latex)
        return m.group(1) if m else None

    @staticmethod
    def _passage_skeleton(full_content: str) -> str:
        """Extract passage header + empty sub-items for enumerate counter.

        For passage problems, when rendering --only solutions/hints, we need
        the passage header (\\item[] with \\textsc{Comprehensive Passage}) and
        empty \\item markers for each sub-question so the enumerate counter
        stays correct.
        """
        import re
        lines: list[str] = []

        # Extract the passage header line: \item[]\begin{center}\textsc{...}\end{center}
        header_match = re.search(
            r'(\\item\[\]\\begin\{center\}.*?\\end\{center\})',
            full_content,
        )
        if header_match:
            lines.append(header_match.group(1))

        # Count sub-question \item markers (not \item[])
        sub_items = re.findall(r'(?<!\\item\[)\\item\s+(?!\[\])', full_content)
        for _ in sub_items:
            lines.append("\\item[]")

        return "\n".join(lines) if lines else "\\item[]"

    def _assemble_problems(self, entries: list[ProblemEntry]) -> int:
        """Stitch solutions and hints from separate dirs into scans/ problem files.

        Returns count of files updated.
        """
        updated = 0
        for entry in entries:
            scan_path = self.base_dir / "scans" / entry.filename
            if not scan_path.exists():
                continue
            current = scan_path.read_text(encoding="utf-8")
            additions: list[str] = []

            # Stitch solution if not already present
            if "\\begin{solution}" not in current:
                sol_path = self.base_dir / "solutions" / entry.filename
                if sol_path.exists():
                    sol_tex = sol_path.read_text(encoding="utf-8")
                    sol_block = self._extract_env_block(sol_tex, "solution")
                    if sol_block:
                        additions.append(sol_block)

            # Stitch alternate solution if not already present
            if "\\begin{alternatesolution}" not in current:
                sol_path = self.base_dir / "solutions" / entry.filename
                if sol_path.exists():
                    sol_tex = sol_path.read_text(encoding="utf-8")
                    alt_block = self._extract_env_block(sol_tex, "alternatesolution")
                    if alt_block:
                        additions.append(alt_block)

            # Stitch idea/remark from solutions file if not already present
            for env in ("idea", "remark"):
                if f"\\begin{{{env}}}" not in current:
                    sol_path = self.base_dir / "solutions" / entry.filename
                    if sol_path.exists():
                        sol_tex = sol_path.read_text(encoding="utf-8")
                        env_block = self._extract_env_block(sol_tex, env)
                        if env_block:
                            additions.append(env_block)

            # Stitch hint if not already present
            if "\\begin{hint}" not in current:
                hint_path = self.base_dir / "hints" / entry.filename
                if hint_path.exists():
                    hint_text = hint_path.read_text(encoding="utf-8").strip()
                    if hint_text:
                        additions.append(
                            f"\\begin{{hint}}\n{hint_text}\n\\end{{hint}}"
                        )

            if additions:
                combined = current.rstrip() + "\n\n" + "\n\n".join(additions) + "\n"
                scan_path.write_text(format_tex(combined), encoding="utf-8")
                updated += 1

        return updated

    def export_zip(
        self,
        output: str = "paper_export.zip",
        title: Optional[str] = None,
        all_packages: bool = False,
        problems: Optional[list[int]] = None,
    ) -> str:
        """Assemble and export an Overleaf-ready zip with main.tex + scans/.

        Returns path to the zip file.
        """
        import shutil
        import tempfile

        # First compile main.tex (assembles everything)
        self.compile_paper(
            output="main.tex", title=title, all_packages=all_packages,
            run_pdflatex=False, problems=problems,
        )

        state = self.manifest.load()
        entries = state.problems
        if problems:
            entries = [p for p in entries if p.serial in problems]

        # Build zip: main.tex + scans/*.tex
        with tempfile.TemporaryDirectory() as tmp:
            export_dir = Path(tmp) / "paper"
            export_dir.mkdir()

            # Copy main.tex
            shutil.copy2(self.base_dir / "main.tex", export_dir / "main.tex")

            # Copy scans/
            scans_out = export_dir / "scans"
            scans_out.mkdir()
            for entry in entries:
                src = self.base_dir / "scans" / entry.filename
                if src.exists():
                    shutil.copy2(src, scans_out / entry.filename)

            # Create zip
            zip_path = self.base_dir / output.replace(".zip", "")
            archive = shutil.make_archive(str(zip_path), "zip", tmp, "paper")
            self.console.print(f"[green]✓[/green] Exported: {archive}")
            return archive

    def _load_syllabus(self) -> None:
        syllabus_path = self.base_dir / "syllabus.json"
        if syllabus_path.exists() and not self.syllabus_mgr.syllabus:
            self.syllabus_mgr = SyllabusManager.load(syllabus_path)
