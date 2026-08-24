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
    classification_fingerprint,
    to_primary_classification,
    to_diagram_analysis,
)
from vbagent.pipeline.io import (
    combine_tikz_artifacts,
    has_main_diagram_placeholder,
    has_tikz_placeholder,
    has_standalone_main_tikz,
    insert_tikz_into_latex,
    remove_main_diagram_placeholder,
    split_tikz_artifacts,
)
from vbagent.cli.common import format_latex, _get_console
from vbagent.references.samples import get_sample


_MATCH_SCAN_CONTRACT_VERSION = 2
_MATCH_TIKZ_CONTRACT_VERSION = 1
_PASSAGE_OPTION_SCAN_CONTRACT_VERSION = 1
_PASSAGE_OPTION_TIKZ_CONTRACT_VERSION = 1
_ASSERTION_DIAGRAM_SCAN_CONTRACT_VERSION = 1
_SUBJECTIVE_STRUCTURE_SCAN_CONTRACT_VERSION = 1


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
        dependency_fingerprint = classification_fingerprint(classification)

        # Load golden sample
        sample = get_sample(primary.subject, primary.question_type)
        if sample:
            self.console.print(f"[dim]Loaded sample: {primary.subject}/{primary.question_type}[/dim]")

        # Decide what to run
        # A positive main-diagram classification has already passed the
        # complete, subject-specific metadata contract.
        needs_tikz = bool(classification.has_diagram)
        needs_options = bool(classification.has_option_diagrams)

        # Check cache
        scan_cached = bool(
            cache and problem_id and cache.has(problem_id, "scan")
        )
        if scan_cached:
            scan_cached = self._cache_matches_classification(
                cache,
                problem_id,
                "scan",
                dependency_fingerprint,
            )
            if not scan_cached:
                self.console.print(
                    "[dim]Ignoring cached scan: classification dependency "
                    "changed or is missing.[/dim]"
                )
        if scan_cached and primary.question_type == "match":
            scan_cached = (
                cache.get_stage_data(problem_id, "scan").get(
                    "match_table_contract_version"
                ) == _MATCH_SCAN_CONTRACT_VERSION
            )
        if scan_cached and primary.question_type == "passage":
            scan_cached = (
                cache.get_stage_data(problem_id, "scan").get(
                    "passage_option_contract_version"
                ) == _PASSAGE_OPTION_SCAN_CONTRACT_VERSION
            )
        if scan_cached and primary.question_type == "assertion_reason":
            scan_cached = (
                cache.get_stage_data(problem_id, "scan").get(
                    "assertion_diagram_contract_version"
                ) == _ASSERTION_DIAGRAM_SCAN_CONTRACT_VERSION
            )
        if scan_cached and primary.question_type == "subjective":
            scan_cached = (
                cache.get_stage_data(problem_id, "scan").get(
                    "subjective_structure_contract_version"
                ) == _SUBJECTIVE_STRUCTURE_SCAN_CONTRACT_VERSION
            )
        tikz_cached = bool(
            cache and problem_id and cache.has(problem_id, "tikz")
        )
        if tikz_cached:
            tikz_cached = self._cache_matches_classification(
                cache,
                problem_id,
                "tikz",
                dependency_fingerprint,
            )
            if not tikz_cached:
                self.console.print(
                    "[dim]Ignoring cached TikZ: classification dependency "
                    "changed or is missing.[/dim]"
                )
        if tikz_cached and primary.question_type == "match":
            tikz_cached = (
                cache.get_stage_data(problem_id, "tikz").get(
                    "match_table_contract_version"
                ) == _MATCH_TIKZ_CONTRACT_VERSION
            )
        options_cached = bool(
            cache and problem_id and cache.has(problem_id, "options")
        )
        if options_cached:
            options_cached = self._cache_matches_classification(
                cache,
                problem_id,
                "options",
                dependency_fingerprint,
            )
            if not options_cached:
                self.console.print(
                    "[dim]Ignoring cached option diagrams: classification "
                    "dependency changed or is missing.[/dim]"
                )
        if options_cached and primary.question_type == "passage":
            options_cached = (
                cache.get_stage_data(problem_id, "options").get(
                    "passage_option_contract_version"
                ) == _PASSAGE_OPTION_TIKZ_CONTRACT_VERSION
            )

        if scan_cached and (tikz_cached or not needs_tikz) and (options_cached or not needs_options):
            self.console.print("[dim]Loading from cache...[/dim]")
            latex = cache.get(problem_id, "scan")
            tikz_code = (
                cache.get(problem_id, "tikz")
                if tikz_cached and needs_tikz
                else None
            )
            option_tikz = cache.get(problem_id, "options") if options_cached else None
            tikz_code = combine_tikz_artifacts(tikz_code, option_tikz)
        else:
            # Parallel dispatch: scan ∥ tikz ∥ options (3-way)
            latex, tikz_code, option_tikz = self._run_parallel(
                image_path, primary, diagram_analysis, sample,
                scan_cached, tikz_cached, options_cached, cache, problem_id,
                needs_tikz=needs_tikz, needs_options=needs_options,
                classification_fingerprint=dependency_fingerprint,
            )

        if primary.question_type == "subjective":
            from vbagent.agents.content_generation.scanner import (
                _has_forbidden_subjective_structure,
            )

            if _has_forbidden_subjective_structure(latex):
                raise ValueError(
                    "Subjective scan contains forbidden MCQ option structure"
                )

        # Option-only questions must not acquire a second, composite "main"
        # diagram. A genuine main + option question has both flags true and
        # keeps both independent generation paths.
        option_only = needs_options and not needs_tikz
        if option_only and has_main_diagram_placeholder(latex):
            latex = remove_main_diagram_placeholder(latex)

        # The scan is downstream evidence. If a non-option-only scan contains
        # a main placeholder despite classification, self-heal the miss.
        main_artifact, option_artifact = split_tikz_artifacts(tikz_code)
        if (not option_only and has_main_diagram_placeholder(latex)
                and not has_standalone_main_tikz(tikz_code)):
            main_artifact = self._run_main_diagram_sync(
                image_path,
                primary,
                diagram_analysis,
                cache=cache,
                problem_id=problem_id,
                classification_fingerprint=dependency_fingerprint,
            )
            tikz_code = combine_tikz_artifacts(main_artifact, option_artifact)

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
        if not has_tikz_placeholder(latex):
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
        classification_fingerprint=None,
    ) -> str:
        """Generate a main diagram when the scanner exposes a classifier miss."""
        from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing

        self.console.print(
            "[yellow]Diagram placeholder found after no-diagram classification; "
            "generating TikZ...[/yellow]"
        )
        description = self._main_diagram_description(primary, diagram_analysis)
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
            stage_data = self._tikz_stage_data(
                primary.question_type,
                classification_fingerprint,
            )
            cache.set(problem_id, "tikz", code, stage_data=stage_data)
        self.console.print(f"[green]OK[/green] TikZ complete [dim]{agent}[/dim]")
        return code

    @staticmethod
    def _main_diagram_description(primary, diagram_analysis) -> str:
        """Describe the required problem-diagram artifact without role mixing."""
        diagram_type = (
            diagram_analysis.diagram_type
            if diagram_analysis and diagram_analysis.diagram_type
            else "diagram"
        )
        if primary.question_type == "match":
            return (
                f"Reconstruct the {diagram_type} diagrams according to their "
                "structural role in this match-the-column question. For every "
                "diagram located inside a Column-I or Column-II row, output one "
                "separate self-contained definition named from its source row "
                "label, for example \\def\\MatchA{\\begin{tikzpicture}"
                "...\\end{tikzpicture}}. Include "
                "baseline=(current bounding box.center). Do not combine table "
                "rows into one montage and do not draw row labels inside the "
                "TikZ pictures. If a genuinely separate standalone diagram "
                "also exists outside the table, output that standalone "
                "tikzpicture first, followed by the \\def\\MatchX definitions. "
                "Ignore diagrams inside selectable answer options, do not "
                "output any \\def\\Option definitions, and output no table or "
                "question text."
            )
        return (
            f"Reconstruct only the standalone main {diagram_type} diagram in "
            "the question stem. Ignore every diagram inside the answer options. "
            "Do not output any \\def\\Option definitions. If the main diagram "
            "is a collection of independently labeled figures that the student "
            "must compare, classify, or discuss, preserve every figure as its "
            "own locally defined panel command and lay the panels out with "
            "multicols plus enumerate. Let enumerate own the labels; do not "
            "combine the panels into one shifted-scope TikZ canvas."
        )

    def _run_scan(
        self,
        image_path,
        primary,
        sample,
        cache,
        problem_id,
        classification_fingerprint=None,
    ) -> str:
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
            stage_data = self._scan_stage_data(
                primary.question_type,
                classification_fingerprint,
            )
            cache.set(
                problem_id,
                "scan",
                latex,
                stage_data=stage_data,
            )

        return latex

    def _run_parallel(self, image_path, primary, diagram_analysis, sample,
                      scan_cached, tikz_cached, options_cached, cache, problem_id,
                      needs_tikz=False, needs_options=False,
                      classification_fingerprint=None):
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
                    stage_data = self._scan_stage_data(
                        primary.question_type,
                        classification_fingerprint,
                    )
                    cache.set(
                        problem_id,
                        "scan",
                        result,
                        stage_data=stage_data,
                    )
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
                desc = self._main_diagram_description(primary, diagram_analysis)
                # For biology: use diagram_draw_description if available
                if (diagram_analysis
                        and hasattr(diagram_analysis, 'diagram_draw_description')
                        and diagram_analysis.diagram_draw_description):
                    desc = f"{diagram_analysis.diagram_draw_description}\n\n{desc}"
                code, agent = generate_tikz_with_routing(
                    image_path=image_path,
                    description=desc,
                    diagram=diagram_analysis,
                    primary=primary,
                    use_context=self.use_context,
                    show_spinner=True,
                    diagram_context="problem",
                )
                tikz_holder["result"] = code
                tikz_holder["agent"] = agent
                state["tikz"]["agent"] = agent
                # Cache immediately
                if cache and problem_id and code:
                    stage_data = self._tikz_stage_data(
                        primary.question_type,
                        classification_fingerprint,
                    )
                    cache.set(
                        problem_id,
                        "tikz",
                        code,
                        stage_data=stage_data,
                    )
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
                    stage_data = self._option_stage_data(
                        primary.question_type,
                        classification_fingerprint,
                    )
                    cache.set(
                        problem_id,
                        "options",
                        tikz_code,
                        stage_data=stage_data,
                    )
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
        if (primary.question_type != "subjective"
                and not run_options
                and latex
                and (r'\OptionA' in latex or r'\OptionB' in latex)):
            option_tikz = self._run_option_diagrams_sync(image_path, primary, diagram_analysis)

        tikz_code = combine_tikz_artifacts(tikz_code, option_tikz)

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

    @staticmethod
    def _cache_matches_classification(
        cache,
        problem_id: str,
        stage: str,
        expected_fingerprint: str,
    ) -> bool:
        """Return whether a cached artifact belongs to this classification."""
        return cache.get_stage_data(problem_id, stage).get(
            "classification_fingerprint"
        ) == expected_fingerprint

    @staticmethod
    def _with_classification_fingerprint(
        stage_data: Optional[dict],
        fingerprint: Optional[str],
    ) -> Optional[dict]:
        """Attach the final-classification dependency to stage metadata."""
        if fingerprint is None:
            return stage_data
        return {
            **(stage_data or {}),
            "classification_fingerprint": fingerprint,
        }

    @classmethod
    def _scan_stage_data(
        cls,
        question_type: str,
        fingerprint: Optional[str] = None,
    ) -> Optional[dict]:
        """Return prompt-contract metadata for cached scan artifacts."""
        stage_data = None
        if question_type == "match":
            stage_data = {
                "match_table_contract_version": _MATCH_SCAN_CONTRACT_VERSION
            }
        elif question_type == "passage":
            stage_data = {
                "passage_option_contract_version":
                    _PASSAGE_OPTION_SCAN_CONTRACT_VERSION
            }
        elif question_type == "assertion_reason":
            stage_data = {
                "assertion_diagram_contract_version":
                    _ASSERTION_DIAGRAM_SCAN_CONTRACT_VERSION
            }
        elif question_type == "subjective":
            stage_data = {
                "subjective_structure_contract_version":
                    _SUBJECTIVE_STRUCTURE_SCAN_CONTRACT_VERSION
            }
        return cls._with_classification_fingerprint(stage_data, fingerprint)

    @classmethod
    def _tikz_stage_data(
        cls,
        question_type: str,
        fingerprint: Optional[str] = None,
    ) -> Optional[dict]:
        """Return contract metadata for cached main-diagram artifacts."""
        stage_data = None
        if question_type == "match":
            stage_data = {
                "match_table_contract_version": _MATCH_TIKZ_CONTRACT_VERSION
            }
        return cls._with_classification_fingerprint(stage_data, fingerprint)

    @classmethod
    def _option_stage_data(
        cls,
        question_type: str,
        fingerprint: Optional[str] = None,
    ) -> Optional[dict]:
        """Return contract metadata for cached option-diagram artifacts."""
        stage_data = None
        if question_type == "passage":
            stage_data = {
                "passage_option_contract_version":
                    _PASSAGE_OPTION_TIKZ_CONTRACT_VERSION
            }
        return cls._with_classification_fingerprint(stage_data, fingerprint)


def create_problem_orchestrator(use_context: bool = True, console=None) -> ProblemOrchestrator:
    """Factory function for ProblemOrchestrator."""
    return ProblemOrchestrator(use_context=use_context, console=console)
