"""Content-generation agents with side-effect-free lazy exports."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .alternate import (
        count_alternate_solutions,
        extract_answer,
        extract_existing_alternates,
        generate_alternate,
        has_alternate_solution,
    )
    from .converter import convert_format
    from .idea import (
        count_idea_environments,
        extract_ideas,
        generate_idea_latex,
        has_idea_environment,
    )
    from .idea_combiner import CombinedProblemOutput, combine_ideas
    from .idea_curator import CurationResult, curate_ideas
    from .idea_generator import generate_from_idea
    from .problem_combiner import combine_problems
    from .scanner import (
        create_scanner_agent,
        scan,
        scan_problem,
        scan_solution,
        scan_with_type,
    )

__all__ = [
    "scan",
    "scan_with_type",
    "scan_problem",
    "scan_solution",
    "create_scanner_agent",
    "extract_ideas",
    "generate_idea_latex",
    "has_idea_environment",
    "count_idea_environments",
    "generate_alternate",
    "extract_answer",
    "extract_existing_alternates",
    "has_alternate_solution",
    "count_alternate_solutions",
    "convert_format",
    "generate_from_idea",
    "curate_ideas",
    "CurationResult",
    "combine_ideas",
    "CombinedProblemOutput",
    "combine_problems",
]


def __getattr__(name: str):
    """Load only the content-generation module that owns the requested name."""
    if name in {
        "scan",
        "scan_with_type",
        "scan_problem",
        "scan_solution",
        "create_scanner_agent",
    }:
        from . import scanner

        return getattr(scanner, name)
    if name in {
        "extract_ideas",
        "generate_idea_latex",
        "has_idea_environment",
        "count_idea_environments",
    }:
        from . import idea

        return getattr(idea, name)
    if name in {
        "generate_alternate",
        "extract_answer",
        "extract_existing_alternates",
        "has_alternate_solution",
        "count_alternate_solutions",
    }:
        from . import alternate

        return getattr(alternate, name)
    if name == "convert_format":
        from . import converter

        return converter.convert_format
    if name == "generate_from_idea":
        from . import idea_generator

        return idea_generator.generate_from_idea
    if name in {"curate_ideas", "CurationResult"}:
        from . import idea_curator

        return getattr(idea_curator, name)
    if name in {"combine_ideas", "CombinedProblemOutput"}:
        from . import idea_combiner

        return getattr(idea_combiner, name)
    if name == "combine_problems":
        from . import problem_combiner

        return problem_combiner.combine_problems
    raise AttributeError(name)
