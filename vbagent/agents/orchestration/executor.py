"""Solution executor - executes plan by calling specialist agents."""

from pathlib import Path
from typing import Union

from vbagent.agents.base import create_agent, run_agent_sync, create_image_message
from vbagent.agents.diagram.physics import create_fbd_agent
from vbagent.agents.diagram.tikz import create_tikz_agent
from vbagent.agents.content_generation.scanner import create_scanner_agent
from vbagent.models.orchestration import SolutionPlan, AgentCall, AgentOutput


class SolutionExecutor:
    """Executes solution plan by coordinating specialist agents."""
    
    def __init__(self):
        """Initialize executor."""
        self._agents = {}
    
    def _get_agent(self, agent_type: str, subject: str = None):
        """Get or create specialist agent.
        
        Args:
            agent_type: Type of agent (fbd, circuit, tikz, etc.)
            subject: Subject for routing (physics, chemistry, mathematics)
            
        Returns:
            Agent instance
        """
        cache_key = f"{agent_type}_{subject}" if subject else agent_type
        
        if cache_key not in self._agents:
            if agent_type == "fbd":
                self._agents[cache_key] = create_fbd_agent()
            elif agent_type in ["circuit", "graph", "ray_diagram", "optics"]:
                self._agents[cache_key] = create_tikz_agent(agent_type)
            elif agent_type == "tikz":
                # For tikz, use subject-specific routing if available
                if subject and subject.lower() == "chemistry":
                    # Use organic chemistry orchestrator for chemistry diagrams
                    # Return a callable that will route properly
                    self._agents[cache_key] = "chemistry_tikz"  # Special marker
                else:
                    self._agents[cache_key] = create_tikz_agent(agent_type)
            elif agent_type in ["text", "calculus", "table"]:
                self._agents[cache_key] = create_scanner_agent()
            else:
                # Default to generic tikz
                self._agents[cache_key] = create_tikz_agent()
        
        return self._agents[cache_key]
    
    def execute(
        self,
        plan: SolutionPlan,
        image_path: Union[str, Path],
        subject: str = None,
    ) -> list[AgentOutput]:
        """Execute plan by calling specialist agents.
        
        Args:
            plan: Solution plan to execute
            image_path: Path to solution image
            subject: Subject for routing (physics, chemistry, mathematics)
            
        Returns:
            List of agent outputs
        """
        outputs = []
        
        for call in plan.agent_calls:
            try:
                output = self._execute_agent_call(call, image_path, subject)
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
        subject: str = None,
    ) -> AgentOutput:
        """Execute a single agent call.
        
        Args:
            call: Agent call specification
            image_path: Path to image
            subject: Subject for routing
            
        Returns:
            Agent output
        """
        agent = self._get_agent(call.agent, subject)
        
        # Special handling for chemistry tikz - use orchestrator
        if agent == "chemistry_tikz":
            from vbagent.agents.diagram.chemistry import generate_organic_orchestrated
            
            # Build description from instruction
            description = call.instruction
            if call.context:
                description += f"\n\nContext: {call.context}"
            if call.image_focus:
                description += f"\n\nFocus: {call.image_focus}"
            
            # Detect if this is MCQ with option diagrams
            mcq_options = False
            if call.context:
                context_lower = call.context.lower()
                mcq_options = (
                    "mcq" in context_lower or
                    "option" in context_lower or
                    "\\optiona" in call.instruction.lower() or
                    "answer choice" in context_lower
                )
            
            try:
                tikz_code = generate_organic_orchestrated(
                    image_path=str(image_path),
                    description=description,
                    use_context=True,
                    show_spinner=True,
                    mcq_options=mcq_options,
                )
                
                return AgentOutput(
                    agent=call.agent,
                    placement=call.placement,
                    content=tikz_code,
                    success=True,
                )
            except Exception as e:
                return AgentOutput(
                    agent=call.agent,
                    placement=call.placement,
                    content="",
                    success=False,
                    error=str(e),
                )
        
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
