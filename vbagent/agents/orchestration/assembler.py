"""Solution assembler - combines agent outputs into final solution."""

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.models.orchestration import SolutionPlan, AgentOutput, SolutionResult
from vbagent.prompts.solution_orchestrator import get_assembler_prompt


class SolutionAssembler:
    """Assembles agent outputs into final unified solution."""
    
    def __init__(self, model: str = "gpt-5.2", temperature: float = 0.2):
        """Initialize assembler.
        
        Args:
            model: Model to use for assembly
            temperature: Temperature for generation
        """
        self.model = model
        self.temperature = temperature
        self._agent = None
    
    def _get_agent(self):
        """Lazy load agent."""
        if self._agent is None:
            self._agent = create_agent(
                name="SolutionAssembler",
                instructions=get_assembler_prompt(),
                agent_type="assembler",
                model=self.model,
                temperature=self.temperature,
            )
        return self._agent
    
    def assemble(
        self,
        plan: SolutionPlan,
        agent_outputs: list[AgentOutput],
    ) -> SolutionResult:
        """Assemble agent outputs into final solution.
        
        Args:
            plan: Original solution plan
            agent_outputs: Outputs from specialist agents
            
        Returns:
            Complete assembled solution
        """
        agent = self._get_agent()
        
        # Build assembly context
        outputs_text = "\n\n".join([
            f"[{output.placement}] ({output.agent})\n{output.content}"
            for output in agent_outputs
            if output.success
        ])
        
        user_message = f"""Assemble the following components into a complete solution.

Solution Structure: {plan.structure}
Steps: {', '.join(plan.steps)}
Assembly Order: {', '.join(plan.assembly_order)}

Components:
{outputs_text}

Create a unified, well-formatted LaTeX solution that:
1. Follows the assembly order
2. Integrates all components smoothly
3. Maintains proper LaTeX structure
4. Ensures diagrams are placed correctly
5. Has clear step-by-step flow

Return only the complete solution LaTeX code."""

        latex = run_agent_sync(agent, user_message)
        
        return SolutionResult(
            latex=latex,
            plan=plan,
            agent_outputs=agent_outputs,
            metadata={
                "successful_agents": sum(1 for o in agent_outputs if o.success),
                "failed_agents": sum(1 for o in agent_outputs if not o.success),
            }
        )
