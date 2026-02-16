"""Solution executor - executes plan by calling specialist agents."""

from pathlib import Path
from typing import Union

from vbagent.agents.base import create_agent, run_agent_sync, create_image_message
from vbagent.agents.diagram.fbd import create_fbd_agent
from vbagent.agents.diagram.tikz import create_tikz_agent
from vbagent.agents.content_generation.scanner import create_scanner_agent
from vbagent.models.orchestration import SolutionPlan, AgentCall, AgentOutput


class SolutionExecutor:
    """Executes solution plan by coordinating specialist agents."""
    
    def __init__(self):
        """Initialize executor."""
        self._agents = {}
    
    def _get_agent(self, agent_type: str):
        """Get or create specialist agent.
        
        Args:
            agent_type: Type of agent (fbd, circuit, tikz, etc.)
            
        Returns:
            Agent instance
        """
        if agent_type not in self._agents:
            if agent_type == "fbd":
                self._agents[agent_type] = create_fbd_agent()
            elif agent_type in ["circuit", "graph", "ray_diagram", "optics", "tikz"]:
                self._agents[agent_type] = create_tikz_agent(agent_type)
            elif agent_type in ["text", "calculus", "table"]:
                self._agents[agent_type] = create_scanner_agent()
            else:
                # Default to generic tikz
                self._agents[agent_type] = create_tikz_agent()
        
        return self._agents[agent_type]
    
    def execute(
        self,
        plan: SolutionPlan,
        image_path: Union[str, Path],
    ) -> list[AgentOutput]:
        """Execute plan by calling specialist agents.
        
        Args:
            plan: Solution plan to execute
            image_path: Path to solution image
            
        Returns:
            List of agent outputs
        """
        outputs = []
        
        for call in plan.agent_calls:
            try:
                output = self._execute_agent_call(call, image_path)
                outputs.append(output)
            except Exception as e:
                outputs.append(AgentOutput(
                    agent=call.agent,
                    placement=call.placement,
                    content="",
                    success=False,
                    error=str(e),
                ))
        
        return outputs
    
    def _execute_agent_call(
        self,
        call: AgentCall,
        image_path: Union[str, Path],
    ) -> AgentOutput:
        """Execute a single agent call.
        
        Args:
            call: Agent call specification
            image_path: Path to image
            
        Returns:
            Agent output
        """
        agent = self._get_agent(call.agent)
        
        # Build message with context
        user_message = f"""{call.instruction}

Context: {call.context}
Placement: {call.placement}
"""
        
        if call.image_focus:
            user_message += f"\nFocus on: {call.image_focus}"
        
        # Create message with image
        message = create_image_message(str(image_path), user_message)
        
        # Run agent
        result = run_agent_sync(agent, message)
        
        # Extract content based on result type
        if isinstance(result, str):
            content = result
        elif hasattr(result, 'latex'):
            content = result.latex
        elif hasattr(result, 'tikz_code'):
            content = result.tikz_code
        else:
            content = str(result)
        
        return AgentOutput(
            agent=call.agent,
            placement=call.placement,
            content=content,
            success=True,
        )
