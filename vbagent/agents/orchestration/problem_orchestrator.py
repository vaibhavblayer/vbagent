"""Problem Orchestrator — deterministic router for the problem pipeline.

Coordinates scanning + TikZ generation based on question classification.
No LLM calls — purely deterministic routing and parallel dispatch.

Flow:
    QuestionClassification → ProblemOrchestrator → (scan ∥ tikz ∥ options) → combined LaTeX
"""

from __future__ import annotations

import threading
from typing import Optional

from vbagent.agents.classification.question_classifier import (
    QuestionClassification,
    to_primary_classification,
    to_diagram_analysis,
)
from vbagent.pipeline.io import (
    insert_tikz_into_latex,
)
from vbagent.cli.common import format_latex, _get_console
from vbagent.references.samples import get_sample


class ProblemResult:
    """Result from the problem orchestrator."""

    __slots__ = ("latex", "tikz_code", "primary", "diagram_analysis", "sample_ref")

    def __init__(self, latex: str, tikz_code: Optional[str], primary, diagram_analysis,
                 sample_ref: Optional[str]):
        self.latex = latex
        self.tikz_code = tikz_code
        self.primary = primary
        self.diagram_analysis = diagram_analysis
        self.sample_ref = sample_ref


class ProblemOrchestrator:
    """Deterministic orchestrator for the problem side of the pipeline.

    Given a QuestionClassification, it:
    1. Loads the golden sample for subject × question_type
    2. Dispatches scanner (with sample as formatting reference)
    3. Dispatches TikZ agent(s) in parallel if needed
    4. Combines everything into final LaTeX
    """

    def __init__(self, use_context: bool = True, console=None):
        self.use_context = use_context
        self.console = console or _get_console()
        from vbagent.ui.logging import AgentLoggingContext, capture_agent_logging_context
        captured = capture_agent_logging_context()
        self._logging_context = AgentLoggingContext(
            console=self.console,
            quiet=captured.quiet,
        )

    def run(
        self,
        image_path: str,
        classification: QuestionClassification,
        cache=None,
        problem_id: Optional[str] = None,
    ) -> ProblemResult:
        """Run the problem pipeline.

        Args:
            image_path: Path to question image
            classification: Question classification result
            cache: Optional PipelineCache
            problem_id: Problem ID for caching

        Returns:
            ProblemResult with combined LaTeX + TikZ
        """
        primary = to_primary_classification(classification)
        diagram_analysis = to_diagram_analysis(classification)

        # Load golden sample
        sample = get_sample(primary.subject, primary.question_type)
        if sample:
            self.console.print(f"[dim]Loaded sample: {primary.subject}/{primary.question_type}[/dim]")

        # Decide what to run
        # If has_diagram is true, generate TikZ even without a specific diagram_type (fall back to generic)
        needs_tikz = bool(classification.has_diagram)
        needs_options = bool(classification.has_option_diagrams)

        # Check cache
        scan_cached = cache and problem_id and cache.has(problem_id, "scan")
        tikz_cached = cache and problem_id and cache.has(problem_id, "tikz")
        options_cached = cache and problem_id and cache.has(problem_id, "options")

        if scan_cached and (tikz_cached or not needs_tikz) and (options_cached or not needs_options):
            self.console.print("[dim]Loading from cache...[/dim]")
            latex = cache.get(problem_id, "scan")
            tikz_code = cache.get(problem_id, "tikz") if tikz_cached else None
            option_tikz = cache.get(problem_id, "options") if options_cached else None
            # Merge options into tikz
            if option_tikz:
                tikz_code = (tikz_code + "\n\n" + option_tikz) if tikz_code else option_tikz
        else:
            # Parallel dispatch: scan ∥ tikz ∥ options (3-way)
            latex, tikz_code, option_tikz = self._run_parallel(
                image_path, primary, diagram_analysis, sample,
                scan_cached, tikz_cached, options_cached, cache, problem_id,
                needs_tikz=needs_tikz, needs_options=needs_options,
            )

        # The scan is downstream evidence. If it contains a main-diagram
        # placeholder despite has_diagram=False, self-heal the classifier miss
        # instead of persisting an unresolved \input{diagram}.
        if latex and r'\input{diagram}' in latex and not tikz_code:
            tikz_code = self._run_main_diagram_sync(
                image_path,
                primary,
                diagram_analysis,
                cache=cache,
                problem_id=problem_id,
            )

        # Combine LaTeX + TikZ
        latex = self._assemble_latex(latex, tikz_code)

        return ProblemResult(
            latex=latex, tikz_code=tikz_code,
            primary=primary, diagram_analysis=diagram_analysis, sample_ref=sample,
        )

    def _assemble_latex(self, latex: Optional[str], tikz_code: Optional[str]) -> Optional[str]:
        """Combine independently cached/generated scan and TikZ artifacts."""
        if not latex or not tikz_code:
            return latex
        if not any(
            marker in latex
            for marker in (r'\input{diagram}', r'\OptionA', r'\OptionB')
        ):
            return latex

        assembled = insert_tikz_into_latex(latex, tikz_code)
        assembled = format_latex(assembled)
        self.console.print("[green]OK[/green] Combined LaTeX + TikZ")
        return assembled

    def _run_main_diagram_sync(
        self,
        image_path,
        primary,
        diagram_analysis,
        cache=None,
        problem_id=None,
    ) -> str:
        """Generate a main diagram when the scanner exposes a classifier miss."""
        from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing

        self.console.print(
            "[yellow]Diagram placeholder found after no-diagram classification; "
            "generating TikZ...[/yellow]"
        )
        description = (
            f"Generate TikZ for {diagram_analysis.diagram_type}"
            if diagram_analysis and diagram_analysis.diagram_type
            else "Reconstruct the diagram shown in the problem image"
        )
        code, agent = generate_tikz_with_routing(
            image_path=image_path,
            description=description,
            diagram=diagram_analysis,
            primary=primary,
            use_context=self.use_context,
            show_spinner=True,
            diagram_context="problem",
        )
        if cache and problem_id and code:
            cache.set(problem_id, "tikz", code)
        self.console.print(f"[green]OK[/green] TikZ complete [dim]{agent}[/dim]")
        return code

    def _run_scan(self, image_path, primary, sample, cache, problem_id) -> str:
        """Run problem-only scanner (no solution extraction)."""
        from vbagent.agents.content_generation.scanner import scan_problem

        self.console.print("[bold green]Scanning image...[/bold green]")
        latex = scan_problem(
            image_path,
            question_type=primary.question_type,
            use_context=self.use_context,
            subject=primary.subject,
            show_spinner=True,
            sample_reference=sample,
        )
        self.console.print("[green]OK[/green] Scan complete")

        if cache and problem_id:
            cache.set(problem_id, "scan", latex)

        return latex

    def _run_parallel(self, image_path, primary, diagram_analysis, sample,
                      scan_cached, tikz_cached, options_cached, cache, problem_id,
                      needs_tikz=False, needs_options=False):
        """Run scan ∥ tikz ∥ options in parallel (up to 3-way).

        Each task caches its result immediately on success so partial
        progress survives errors or user interrupts.
        """
        import time
        from vbagent.agents.content_generation.scanner import scan_problem
        from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
        from vbagent.agents.diagram import generate_mcq_options
        from rich.live import Live
        from rich.text import Text

        SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

        # Determine what runs in parallel
        run_tikz = needs_tikz and not tikz_cached
        run_options = needs_options and not options_cached

        # Build task list: (key, label, agent_hint)
        tasks = [("scan", "Scan", f"Scanner-{primary.question_type}-{primary.subject}")]
        if run_tikz:
            agent_hint = diagram_analysis.suggested_tikz_agent if diagram_analysis else "generic"
            tasks.append(("tikz", "TikZ", agent_hint))
        if run_options:
            tasks.append(("options", "Options", "MCQOptions"))

        n_parallel = len(tasks)
        labels = ", ".join(label for _, label, _ in tasks)
        self.console.print(f"[dim]{labels} ({n_parallel}-way parallel)...[/dim]")

        # State per task
        state = {key: {"status": "pending", "duration": 0.0, "agent": hint}
                 for key, _, hint in tasks}
        start_times = {}
        spin_tick = [0]

        scan_holder = {"result": None, "error": None}
        tikz_holder = {"result": None, "error": None, "agent": "generic"}
        option_holder = {"result": None, "error": None}

        def do_scan():
            from vbagent.ui.logging import apply_agent_logging_context, set_task_tag
            apply_agent_logging_context(self._logging_context)
            set_task_tag("Scan")
            start_times["scan"] = time.time()
            state["scan"]["status"] = "running"
            if scan_cached:
                scan_holder["result"] = cache.get(problem_id, "scan")
                state["scan"]["status"] = "cached"
                state["scan"]["duration"] = time.time() - start_times["scan"]
                return
            try:
                result = scan_problem(
                    image_path,
                    question_type=primary.question_type,
                    use_context=self.use_context,
                    subject=primary.subject,
                    show_spinner=True,
                    sample_reference=sample,
                )
                scan_holder["result"] = result
                # Cache immediately so partial progress survives
                if cache and problem_id:
                    cache.set(problem_id, "scan", result)
                state["scan"]["status"] = "done"
            except Exception as e:
                scan_holder["error"] = e
                state["scan"]["status"] = "failed"
            state["scan"]["duration"] = time.time() - start_times["scan"]

        def do_tikz():
            from vbagent.ui.logging import apply_agent_logging_context, set_task_tag
            apply_agent_logging_context(self._logging_context)
            set_task_tag("TikZ")
            start_times["tikz"] = time.time()
            state["tikz"]["status"] = "running"
            try:
                desc = (f"Generate TikZ for {diagram_analysis.diagram_type}"
                        if diagram_analysis and diagram_analysis.diagram_type
                        else "Generate diagram")
                # For biology: use diagram_draw_description if available
                if (diagram_analysis
                        and hasattr(diagram_analysis, 'diagram_draw_description')
                        and diagram_analysis.diagram_draw_description):
                    desc = diagram_analysis.diagram_draw_description
                code, agent = generate_tikz_with_routing(
                    image_path=image_path,
                    description=desc,
                    diagram=diagram_analysis,
                    primary=primary,
                    use_context=self.use_context,
                    show_spinner=True,
                )
                tikz_holder["result"] = code
                tikz_holder["agent"] = agent
                state["tikz"]["agent"] = agent
                # Cache immediately
                if cache and problem_id and code:
                    cache.set(problem_id, "tikz", code)
                state["tikz"]["status"] = "done"
            except Exception as e:
                tikz_holder["error"] = e
                state["tikz"]["status"] = "failed"
            state["tikz"]["duration"] = time.time() - start_times["tikz"]

        def do_options():
            from vbagent.ui.logging import apply_agent_logging_context, set_task_tag
            apply_agent_logging_context(self._logging_context)
            set_task_tag("Options")
            start_times["options"] = time.time()
            state["options"]["status"] = "running"
            try:
                tikz_code = generate_mcq_options(
                    image_path=image_path,
                    subject=primary.subject,
                    option_diagram_type=(diagram_analysis.option_diagram_type
                                        if diagram_analysis else "organic_structure"),
                    option_descriptions=(diagram_analysis.option_diagram_descriptions
                                        if diagram_analysis else None),
                    diagram_analysis=(diagram_analysis.model_dump()
                                     if diagram_analysis else None),
                    use_context=self.use_context,
                    show_spinner=True,
                )
                option_holder["result"] = tikz_code
                # Cache immediately
                if cache and problem_id and tikz_code:
                    cache.set(problem_id, "options", tikz_code)
                state["options"]["status"] = "done"
            except Exception as e:
                option_holder["error"] = e
                state["options"]["status"] = "failed"
            state["options"]["duration"] = time.time() - start_times["options"]

        def render_status():
            """Render minimal Codex-style status lines."""
            text = Text()
            spin_char = SPINNER[spin_tick[0] % len(SPINNER)]
            spin_tick[0] += 1
            for i, (key, label, _) in enumerate(tasks):
                if i > 0:
                    text.append("\n")
                s = state[key]
                if s["status"] == "pending":
                    text.append("  PENDING ", style="dim")
                    text.append(label, style="dim")
                elif s["status"] == "running":
                    elapsed = time.time() - start_times.get(key, time.time())
                    text.append(f"  {spin_char} ", style="cyan")
                    text.append(f"{label}", style="cyan")
                    text.append(f"  {elapsed:.0f}s", style="dim")
                elif s["status"] == "done":
                    text.append("  OK ", style="green")
                    text.append(label, style="green")
                    text.append(f"  {s['duration']:.1f}s", style="dim")
                elif s["status"] == "cached":
                    text.append("  CACHED ", style="yellow")
                    text.append(label, style="yellow")
                    text.append("  cached", style="dim")
                elif s["status"] == "failed":
                    text.append("  ERROR ", style="red")
                    text.append(label, style="red")
                    text.append(f"  {s['duration']:.1f}s", style="dim")
            return text

        # Start threads
        threads = []
        t_scan = threading.Thread(target=do_scan, daemon=True)
        threads.append(t_scan)
        t_scan.start()

        if run_tikz:
            t_tikz = threading.Thread(target=do_tikz, daemon=True)
            threads.append(t_tikz)
            t_tikz.start()

        if run_options:
            t_opts = threading.Thread(target=do_options, daemon=True)
            threads.append(t_opts)
            t_opts.start()

        # Live status display
        with Live(render_status(), console=self.console,
                  refresh_per_second=8, transient=True) as live:
            while any(t.is_alive() for t in threads):
                live.update(render_status())
                for t in threads:
                    t.join(timeout=0.1)
            live.update(render_status())

        # Print final static status (persists after Live clears)
        for key, label, _ in tasks:
            s = state[key]
            if s["status"] == "done":
                self.console.print(
                    f"  [green]OK[/green] {label} [dim]{s['agent']}  {s['duration']:.1f}s[/dim]")
            elif s["status"] == "cached":
                self.console.print(
                    f"  [yellow]CACHED[/yellow] {label} [dim]cached[/dim]")
            elif s["status"] == "failed":
                self.console.print(
                    f"  [red]ERROR[/red] {label} [dim]{s['agent']}  {s['duration']:.1f}s[/dim]")

        # Process scan result
        if scan_holder["error"]:
            raise scan_holder["error"]
        latex = scan_holder["result"]

        # Process tikz result
        tikz_code = None
        if run_tikz:
            if tikz_holder["error"]:
                self.console.print(
                    f"  [red]TikZ error:[/red] {tikz_holder['error']}"
                )
                raise tikz_holder["error"]
            tikz_code = tikz_holder["result"]
        elif tikz_cached:
            tikz_code = cache.get(problem_id, "tikz")

        # Process option diagrams result
        option_tikz = None
        if run_options:
            if option_holder["error"]:
                self.console.print(
                    f"  [red]Option diagram error:[/red] {option_holder['error']}"
                )
                raise option_holder["error"]
            option_tikz = option_holder["result"]
        elif options_cached:
            option_tikz = cache.get(problem_id, "options")

        # Also check for option markers in scanned latex (even if not flagged by classifier)
        if not run_options and latex and (r'\OptionA' in latex or r'\OptionB' in latex):
            option_tikz = self._run_option_diagrams_sync(image_path, primary, diagram_analysis)

        # Merge: option tikz takes precedence if it contains option definitions
        if option_tikz:
            if tikz_code:
                tikz_code = tikz_code + "\n\n" + option_tikz
            else:
                tikz_code = option_tikz

        return latex, tikz_code, option_tikz

    def _run_option_diagrams_sync(self, image_path, primary, diagram_analysis):
        """Fallback: generate option diagrams synchronously."""
        from vbagent.agents.diagram import generate_mcq_options

        self.console.print("[dim]  → Generating option diagrams...[/dim]")
        try:
            tikz_code = generate_mcq_options(
                image_path=image_path,
                subject=primary.subject,
                option_diagram_type=diagram_analysis.option_diagram_type if diagram_analysis else "organic_structure",
                option_descriptions=diagram_analysis.option_diagram_descriptions if diagram_analysis else None,
                diagram_analysis=diagram_analysis.model_dump() if diagram_analysis else None,
                use_context=self.use_context,
                show_spinner=True,
            )
            self.console.print("[green]  OK Option diagrams complete[/green]")
            return tikz_code
        except Exception as e:
            self.console.print(f"[yellow]  WARN Option diagrams failed: {e}[/yellow]")
            raise


def create_problem_orchestrator(use_context: bool = True, console=None) -> ProblemOrchestrator:
    """Factory function for ProblemOrchestrator."""
    return ProblemOrchestrator(use_context=use_context, console=console)
