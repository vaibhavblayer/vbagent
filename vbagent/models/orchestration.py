"""Data models for solution orchestration."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class AgentCall(BaseModel):
    """Specification for calling a specialist agent."""
    
    agent: Literal["fbd", "circuit", "graph", "ray_diagram", "optics", "calculus", "table", "tikz", "text"]
    instruction: str = Field(description="Specific instruction for this agent")
    context: str = Field(description="Context about where this fits in the solution")
    placement: str = Field(description="Where to place this in the solution (e.g., 'step_2', 'after_equation_3')")
    image_focus: Optional[str] = Field(None, description="Which part of image to focus on")


class SolutionPlan(BaseModel):
    """Plan for generating a complete solution."""
    
    structure: str = Field(description="Overall structure of the solution (e.g., 'multi_step', 'proof', 'direct')")
    steps: list[str] = Field(description="High-level steps in the solution")
    agent_calls: list[AgentCall] = Field(description="Specialist agents to call")
    assembly_order: list[str] = Field(description="Order to assemble components")
    
    
class AgentOutput(BaseModel):
    """Output from a specialist agent."""
    
    agent: str
    placement: str
    content: str = Field(description="Generated LaTeX content")
    success: bool = True
    error: Optional[str] = None


class SolutionResult(BaseModel):
    """Final assembled solution."""
    
    latex: str = Field(description="Complete solution LaTeX")
    plan: SolutionPlan = Field(description="Plan that was executed")
    agent_outputs: list[AgentOutput] = Field(description="Outputs from all agents")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
