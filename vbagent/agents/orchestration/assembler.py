"""Solution assembler - combines agent outputs into final solution."""

import re
from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.models.orchestration import SolutionPlan, AgentOutput, SolutionResult
from vbagent.prompts.solution_orchestrator import get_assembler_prompt


def clean_latex_fences(latex: str) -> str:
    """Remove markdown code fences from LaTeX output."""
    # Remove opening fence: ```latex, ```tex, ```LaTeX, or just ```
    latex = re.sub(r'^```(?:latex|tex|LaTeX)?\s*\n?', '', latex, flags=re.IGNORECASE)
    # Remove closing fence
    latex = re.sub(r'\n?```\s*$', '', latex)
    # Remove any remaining standalone ```
    latex = re.sub(r'^```\s*', '', latex)
    return latex.strip()


class SolutionAssembler:
    """Assembles problem + specialist outputs into final solution."""
    
    def __init__(self, model: str = "gpt-5.2"):
        """Initialize assembler.
        
        Args:
            model: Model to use for assembly
        """
        self.model = model
        self._agent = None
    
    def _get_agent(self):
        """Lazy load agent."""
        if self._agent is None:
            self._agent = create_agent(
                name="SolutionAssembler",
                instructions=get_assembler_prompt(),
                agent_type="assembler",
                model=self.model,
            )
        return self._agent
    
    def assemble(
        self,
        problem_latex: str,
        plan: SolutionPlan,
        agent_outputs: list[AgentOutput],
    ) -> SolutionResult:
        r"""Assemble problem + specialist outputs into final solution.
        
        Args:
            problem_latex: Problem statement from scanner (with \item, options, etc.)
            plan: Original solution plan
            agent_outputs: Outputs from specialist agents
            
        Returns:
            Complete assembled solution (problem + solution)
        """
        agent = self._get_agent()
        
        # Build assembly context
        outputs_text = "\n\n".join([
            f"[{output.placement}] ({output.agent})\n{output.content}"
            for output in agent_outputs
            if output.success
        ])
        
        user_message = f"""Assemble a complete LaTeX document from the problem statement and specialist outputs.

**Problem Statement (already extracted):**
```latex
{problem_latex}
```

**Specialist Outputs:**
{outputs_text}

**Assembly Instructions:**
1. Start with the problem statement AS-IS (do not modify)
2. Add `\\begin{{solution}}...\\end{{solution}}` after the problem
3. Inside solution: integrate specialist outputs in order: {', '.join(plan.assembly_order)}
4. Use `align*` blocks with `\\intertext{{}}` for text
5. Wrap diagrams in `\\begin{{center}}...\\end{{center}}`
6. Keep solution CONCISE - key steps only

**Output:** Complete LaTeX starting with `\\item` and ending with `\\end{{solution}}`.

Return only the complete solution LaTeX code."""

        latex = run_agent_sync(agent, user_message)
        
        # Clean code fences if present
        latex = clean_latex_fences(latex)
        
        return SolutionResult(
            latex=latex,
            plan=plan,
            agent_outputs=agent_outputs,
            metadata={
                "successful_agents": sum(1 for o in agent_outputs if o.success),
                "failed_agents": sum(1 for o in agent_outputs if not o.success),
            }
        )
