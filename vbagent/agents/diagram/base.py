"""Base class for diagram agents.

Eliminates ~80% boilerplate across 15+ diagram agents by extracting
the shared patterns into a configurable DiagramAgent class.

Two agent patterns are supported:
- "rich" (physics): Has reference search tool, classification context via
  TikZReferenceStore, and solution_context/values/labels params.
- "simple" (chemistry/math): No reference tool, uses ReferenceStore with
  a hardcoded search query, simpler generate() signature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.utils.latex import clean_latex_output


@dataclass
class DiagramAgentConfig:
    """Configuration for a diagram agent.

    Attributes:
        name: Agent display name (e.g. "FBD", "EnergyDiagram").
        agent_type: Agent type string passed to create_agent().
        system_prompt: The SYSTEM_PROMPT from the prompt module.
        user_template: USER_TEMPLATE string (has {description} placeholder).
        user_template_from_problem: USER_TEMPLATE_FROM_PROBLEM string.
        diagram_type_filter: Filter for TikZReferenceStore (rich agents only).
        reference_search_query: Search query for ReferenceStore (simple agents).
        reference_tool_name: Name for the lazy reference tool (rich agents).
        reference_tool_docstring: Docstring for the reference tool.
        reference_no_results_msg: Message when no references found.
        validation_markers: List of strings to check in validate output.
        validation_required_commands: Commands that must be present (e.g. \\ce{).
        validation_return_tuple: If True, validate returns (bool, str); else bool.
        solution_context_hint: Hint appended after solution_context in prompt.
        problem_template_key: The format key in user_template_from_problem
            (e.g. "problem_text" for physics, "problem" for chem/math).
        has_rich_context: Whether agent supports solution_context/values/labels.
    """

    name: str
    agent_type: str
    system_prompt: str
    user_template: str
    user_template_from_problem: str
    diagram_type_filter: str | None = None
    reference_search_query: str | None = None
    reference_tool_name: str | None = None
    reference_tool_docstring: str | None = None
    reference_no_results_msg: str = "No relevant references found."
    validation_markers: list[str] = field(default_factory=list)
    validation_required_commands: list[str] = field(default_factory=list)
    validation_return_tuple: bool = False
    custom_validator: object = None  # Optional callable(str) -> bool | tuple[bool,str]
    solution_context_hint: str = ""
    problem_template_key: str = "problem"
    has_rich_context: bool = False


class DiagramAgent:
    """Reusable diagram agent that encapsulates the shared generation pattern.

    Usage::

        config = DiagramAgentConfig(name="FBD", ...)
        agent = DiagramAgent(config)

        # Then expose module-level functions:
        create_fbd_agent = agent.create_agent
        generate_fbd = agent.generate
        validate_fbd_output = agent.validate
        get_fbd_context_for_classification = agent.get_context_for_classification
    """

    def __init__(self, config: DiagramAgentConfig):
        self.config = config
        self._reference_tool = None

    # ------------------------------------------------------------------
    # Reference tool (lazy, only for rich agents)
    # ------------------------------------------------------------------

    def _get_reference_tool(self):
        """Create the reference search tool lazily (rich agents only)."""
        if self._reference_tool is not None:
            return self._reference_tool

        if not self.config.reference_tool_name:
            return None

        from agents import function_tool
        from vbagent.references.store import ReferenceStore

        tool_name = self.config.reference_tool_name
        docstring = self.config.reference_tool_docstring or (
            f"Search reference files for {self.config.name} examples."
        )
        no_results = self.config.reference_no_results_msg

        @function_tool(name_override=tool_name)
        def _search_reference(query: str) -> str:
            store = ReferenceStore.get_instance()
            results = store.search(query, file_types=["sty", "tex", "pdf"])
            if not results:
                return no_results
            parts = []
            for r in results[:3]:
                parts.append(f"--- From {r.file_path} ---\n{r.content}")
            return "\n\n".join(parts)

        _search_reference.__doc__ = docstring
        self._reference_tool = _search_reference
        return self._reference_tool

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def get_context_for_classification(self, classification=None) -> str:
        """Get context matched to classification metadata.

        Rich agents use TikZReferenceStore with diagram_type_filter.
        Simple agents use ReferenceStore with a search query.
        """
        if self.config.has_rich_context and classification is not None:
            return self._get_rich_context(classification)
        return self._get_simple_context()

    def _get_rich_context(self, classification) -> str:
        try:
            from vbagent.references.tikz_store import TikZReferenceStore

            store = TikZReferenceStore.get_instance()
            context = store.get_context_for_classification(
                classification,
                diagram_type_filter=self.config.diagram_type_filter,
            )
            if not context:
                return ""
            return (
                f"\n## Matching {self.config.name} Examples\n\n"
                f"The following examples match your problem type. "
                f"Use them as style references:\n\n{context}\n\n---\n"
            )
        except Exception:
            return ""

    def _get_simple_context(self) -> str:
        if not self.config.reference_search_query:
            return ""
        from vbagent.references.store import ReferenceStore

        store = ReferenceStore()
        results = store.search(
            query=self.config.reference_search_query,
            file_types=["sty", "tex", "pdf"],
            max_results=3,
        )
        if not results:
            return ""
        ctx = "\n\n## Reference Examples\n\n"
        ctx += f"Here are some similar {self.config.name} diagrams from our reference library:\n\n"
        for i, r in enumerate(results, 1):
            ctx += f"### Example {i}\n```latex\n{r.content}\n```\n\n"
        return ctx

    # ------------------------------------------------------------------
    # Agent creation
    # ------------------------------------------------------------------

    def create_agent(
        self,
        use_context: bool = True,
        classification=None,
        problem_text: str | None = None,
        solution_context: str | None = None,
        values: dict | None = None,
        labels: list | None = None,
    ):
        """Create a configured Agent instance."""
        from vbagent.prompts.diagram._style_discipline import STYLE_DISCIPLINE

        prompt = self.config.system_prompt + "\n" + STYLE_DISCIPLINE

        # Classification context (rich path)
        if use_context and classification and self.config.has_rich_context:
            ctx = self._get_rich_context(classification)
            if ctx:
                prompt += "\n" + ctx

        # Reference context
        if use_context:
            if self.config.has_rich_context:
                from vbagent.references.context import get_context_prompt_section
                ctx = get_context_prompt_section("tikz", use_context)
                if ctx:
                    prompt += "\n" + ctx
            else:
                ctx = self._get_simple_context()
                if ctx:
                    prompt += "\n\n" + ctx

        # Rich context from solution agent (physics agents)
        if self.config.has_rich_context:
            if problem_text:
                prompt += f"\n\n## Problem Context\n\n{problem_text}\n"
            if solution_context:
                prompt += f"\n\n## Solution Analysis\n\n{solution_context}\n"
                if self.config.solution_context_hint:
                    prompt += f"\n{self.config.solution_context_hint}\n"
            if values:
                values_str = ", ".join(f"{k}={v}" for k, v in values.items())
                prompt += f"\n\n## Values to Use\n\n{values_str}\n"
            if labels:
                labels_str = ", ".join(labels)
                prompt += f"\n\n## Labels Required\n\n{labels_str}\n"
                prompt += "\nEnsure all these labels appear in the diagram.\n"

        tools = []
        ref_tool = self._get_reference_tool()
        if ref_tool:
            tools.append(ref_tool)

        return create_agent(
            name=self.config.name,
            instructions=prompt,
            tools=tools if tools else [],
            agent_type=self.config.agent_type,
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        description: str = "",
        image_path: str | None = None,
        problem_text: str | None = None,
        search_references: bool = True,
        use_context: bool = True,
        classification=None,
        show_spinner: bool = True,
        solution_context: str | None = None,
        values: dict | None = None,
        labels: list | None = None,
    ) -> str:
        """Generate diagram code.

        Rich agents accept all params. Simple agents ignore
        solution_context/values/labels/classification/search_references.
        """
        # Validate inputs
        if self.config.has_rich_context:
            if not description and not image_path and not problem_text:
                raise ValueError(
                    "Must provide at least one of: description, image_path, or problem_text"
                )
        else:
            if not image_path and not description:
                raise ValueError("Either image_path or description must be provided")

        # Create agent
        agent = self.create_agent(
            use_context=use_context,
            classification=classification,
            problem_text=problem_text if self.config.has_rich_context else None,
            solution_context=solution_context if self.config.has_rich_context else None,
            values=values if self.config.has_rich_context else None,
            labels=labels if self.config.has_rich_context else None,
        )

        # Build user message
        user_message = self._build_user_message(
            description=description,
            image_path=image_path,
            problem_text=problem_text,
            solution_context=solution_context,
        )

        # Attach image if provided
        if image_path:
            message = create_image_message(image_path, user_message)
        else:
            message = user_message

        raw_result = run_agent_sync(agent, message, show_spinner=show_spinner, timeout=600)
        return clean_latex_output(raw_result)

    def _build_user_message(
        self,
        description: str = "",
        image_path: str | None = None,
        problem_text: str | None = None,
        solution_context: str | None = None,
    ) -> str:
        """Build the user message from templates."""
        if self.config.has_rich_context:
            # Physics pattern: problem_text in user msg only if no solution_context
            if problem_text and not solution_context:
                msg = self.config.user_template_from_problem.format(
                    **{self.config.problem_template_key: problem_text}
                )
                if description:
                    msg += f"\n\n**Additional context:** {description}"
                return msg
            return self.config.user_template.format(
                description=description or f"Generate {self.config.name} diagram from the provided image"
            )
        else:
            # Simple pattern: image → USER_TEMPLATE, text → USER_TEMPLATE_FROM_PROBLEM
            if image_path:
                return self.config.user_template
            key = self.config.problem_template_key
            return self.config.user_template_from_problem.format(
                **{key: description}
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, code: str) -> bool | tuple[bool, str]:
        """Validate generated code.

        Returns bool or (bool, str) depending on config.validation_return_tuple.
        If a custom_validator is provided, it takes precedence.
        """
        if self.config.custom_validator is not None:
            return self.config.custom_validator(code)
        if self.config.validation_return_tuple:
            return self._validate_tuple(code)
        return self._validate_bool(code)

    def _validate_bool(self, code: str) -> bool:
        if not code or not code.strip():
            return False
        code_lower = code.lower()
        has_tikzpicture = "tikzpicture" in code_lower
        has_draw = any(cmd in code_lower for cmd in ["\\draw", "\\node"])
        markers_ok = all(m.lower() in code_lower or m in code for m in self.config.validation_markers)
        return has_tikzpicture and has_draw and markers_ok

    def _validate_tuple(self, code: str) -> tuple[bool, str]:
        if not code or not code.strip():
            return False, f"Empty {self.config.name} code"

        # Check required commands
        for cmd in self.config.validation_required_commands:
            if cmd not in code:
                return False, f"Missing {cmd}"

        # Check tikzpicture if not a chemfig/mhchem agent
        if not self.config.validation_required_commands:
            if "\\begin{tikzpicture}" not in code:
                return False, "Missing \\begin{tikzpicture}"
            if "\\end{tikzpicture}" not in code:
                return False, "Missing \\end{tikzpicture}"

        # Balanced braces
        if code.count("{") != code.count("}"):
            o, c = code.count("{"), code.count("}")
            return False, f"Unbalanced braces: {o} open, {c} close"

        # Domain-specific markers
        for marker in self.config.validation_markers:
            if marker.lower() not in code.lower() and marker not in code:
                return False, f"Missing expected content: {marker}"

        return True, ""
