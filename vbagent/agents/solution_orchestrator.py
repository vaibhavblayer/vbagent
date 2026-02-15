"""Main solution orchestrator - coordinates planning, execution, and assembly."""

from pathlib import Path
from typing import Union, Optional

from vbagent.agents.orchestration.planner import SolutionPlanner
from vbagent.agents.orchestration.executor import SolutionExecutor
from vbagent.agents.orchestration.assembler import SolutionAssembler
from vbagent.models.orchestration import SolutionResult


class SolutionOrchestrator:
    """Main orchestrator for solution generation.
    
    Coordinates the three-phase process:
    1. Planning: Analyze solution and create execution plan
    2. Execution: Call specialist agents as needed
    3. Assembly: Combine outputs into final solution
    """
    
    def __init__(
        self,
        planner_model: str = "gpt-5.2",
        assembler_model: str = "gpt-5.2",
    ):
        """Initialize orchestrator.
        
        Args:
            planner_model: Model for planning phase
            assembler_model: Model for assembly phase
        """
        self.planner = SolutionPlanner(model=planner_model)
        self.executor = SolutionExecutor()
        self.assembler = SolutionAssembler(model=assembler_model)
    
    def generate_solution(
        self,
        image_path: Union[str, Path],
        problem_context: str = "",
        question_type: str = "subjective",
        verbose: bool = False,
    ) -> SolutionResult:
        """Generate complete solution using orchestration.
        
        Args:
            image_path: Path to solution image
            problem_context: Context about the problem
            question_type: Type of question
            verbose: Print progress information
            
        Returns:
            Complete solution with metadata
        """
        if verbose:
            print("Phase 1: Planning...")
        
        # Phase 1: Create plan
        plan = self.planner.plan(
            image_path=image_path,
            problem_context=problem_context,
            question_type=question_type,
        )
        
        if verbose:
            print(f"  Structure: {plan.structure}")
            print(f"  Steps: {len(plan.steps)}")
            print(f"  Agent calls: {len(plan.agent_calls)}")
            for call in plan.agent_calls:
                print(f"    - {call.agent} at {call.placement}")
        
        if verbose:
            print("\nPhase 2: Executing specialist agents...")
        
        # Phase 2: Execute plan
        agent_outputs = self.executor.execute(
            plan=plan,
            image_path=image_path,
        )
        
        if verbose:
            successful = sum(1 for o in agent_outputs if o.success)
            print(f"  Completed: {successful}/{len(agent_outputs)} agents")
        
        if verbose:
            print("\nPhase 3: Assembling solution...")
        
        # Phase 3: Assemble solution
        result = self.assembler.assemble(
            plan=plan,
            agent_outputs=agent_outputs,
        )
        
        if verbose:
            print("  ✓ Solution assembled")
        
        return result


def create_solution_orchestrator(
    planner_model: Optional[str] = None,
    assembler_model: Optional[str] = None,
) -> SolutionOrchestrator:
    """Create solution orchestrator with optional model overrides.
    
    Args:
        planner_model: Model for planning (uses config default if None)
        assembler_model: Model for assembly (uses config default if None)
        
    Returns:
        SolutionOrchestrator instance
    """
    from vbagent.config import get_config
    
    config = get_config()
    
    if planner_model is None:
        planner_model = config.scanner.model
    
    if assembler_model is None:
        assembler_model = config.scanner.model
    
    return SolutionOrchestrator(
        planner_model=planner_model,
        assembler_model=assembler_model,
    )
