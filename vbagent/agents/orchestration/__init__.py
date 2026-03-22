"""Orchestration system for problem and solution pipelines."""

from vbagent.agents.orchestration.solution_orchestrator import (
    SolutionOrchestrator,
    SolutionResult,
    create_solution_orchestrator,
)
from vbagent.agents.orchestration.problem_orchestrator import (
    ProblemOrchestrator,
    ProblemResult,
    create_problem_orchestrator,
)

__all__ = [
    "SolutionOrchestrator",
    "SolutionResult",
    "create_solution_orchestrator",
    "ProblemOrchestrator",
    "ProblemResult",
    "create_problem_orchestrator",
]
