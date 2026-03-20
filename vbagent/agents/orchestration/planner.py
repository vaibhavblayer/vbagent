"""Solution planner agent - analyzes and creates execution plan."""

from pathlib import Path
from typing import Union

from vbagent.agents.base import create_agent, run_agent_sync, create_image_message
from vbagent.models.orchestration import SolutionPlan
from vbagent.prompts.diagram.solution_orchestrator import get_planner_prompt


class SolutionPlanner:
    """Analyzes solution and creates execution plan."""
    
    def __init__(self, model: str = "gpt-5.2"):
        """Initialize planner.
        
        Args:
            model: Model to use for planning
        """
        self.model = model
        self._agent = None
    
    def _get_agent(self):
        """Lazy load agent."""
        if self._agent is None:
            self._agent = create_agent(
                name="SolutionPlanner",
                instructions=get_planner_prompt(),
                agent_type="planner",
                model=self.model,
                output_type=SolutionPlan,
            )
        return self._agent
    
    def plan(
        self,
        image_path: Union[str, Path],
        problem_context: str = "",
        question_type: str = "subjective",
        subject: str = None,
    ) -> SolutionPlan:
        """Analyze solution and create execution plan.
        
        Args:
            image_path: Path to solution image
            problem_context: Context about the problem
            question_type: Type of question
            subject: Subject (physics, chemistry, mathematics)
            
        Returns:
            SolutionPlan with agent calls and assembly instructions
        """
        agent = self._get_agent()
        
        # Build subject-specific diagram examples
        diagram_examples = {
            "physics": "FBD, circuit, graph, ray diagram, optics",
            "chemistry": "organic structures, mechanisms, energy diagrams, orbital diagrams",
            "mathematics": "function graphs, geometric diagrams, number lines, Venn diagrams",
        }
        
        diagrams_hint = diagram_examples.get(subject, "diagrams") if subject else "diagrams"
        
        # Create message with image
        user_message = f"""Analyze this solution image and create an execution plan.

Problem Context: {problem_context}
Question Type: {question_type}
Subject: {subject or 'unknown'}

Identify:
1. What diagrams are needed ({diagrams_hint})
2. What mathematical complexity (basic algebra, calculus, etc.)
3. Solution structure (single-step, multi-part, proof-based)
4. Which specialist agents to call and in what order

For chemistry diagrams, use the `tikz` agent (it automatically routes to chemistry-specific orchestrator).
For physics diagrams, use specific agents like `fbd`, `circuit`, `graph`, etc.

Return a detailed plan."""

        message = create_image_message(str(image_path), user_message)
        
        # Get plan from agent
        result = run_agent_sync(agent, message)
        
        return result
