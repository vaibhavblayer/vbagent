"""Solution Orchestrator - Intelligent multi-agent solution generation.

This orchestrator analyzes the problem and coordinates multiple specialized agents
to generate high-quality solutions with diagrams, subject-specific formatting,
and question-type-specific approaches.

Architecture:
    Problem → Orchestrator → [Analyze] → [Route] → [Generate] → [Assemble] → Solution
                    ↓
              [Diagram Agent] (if needed)
                    ↓
              [Subject+Type Specific Agent]
"""

from typing import Optional, Literal
from pathlib import Path

from vbagent.models.classification import ClassificationResult
from vbagent.models.solution import SolutionOutput, DiagramRequirement


class SolutionOrchestrator:
    """Orchestrates solution generation with intelligent agent coordination.
    
    This orchestrator:
    1. Analyzes problem needs (diagram, complexity, subject, type)
    2. Routes to appropriate specialized agents
    3. Coordinates diagram generation with rich context
    4. Assembles final solution with proper formatting
    """
    
    def __init__(
        self,
        subject: str,
        question_type: str,
        use_context: bool = True,
        show_spinner: bool = True,
    ):
        """Initialize orchestrator.
        
        Args:
            subject: Subject (physics, chemistry, mathematics)
            question_type: Question type (subjective, mcq_sc, mcq_mc, etc.)
            use_context: Whether to use reference context
            show_spinner: Whether to show progress spinners
        """
        self.subject = subject.lower()
        self.question_type = question_type.lower()
        self.use_context = use_context
        self.show_spinner = show_spinner
    
    def analyze_needs(
        self,
        problem_text: str,
        classification: ClassificationResult,
    ) -> dict:
        """Analyze what the solution needs.
        
        Args:
            problem_text: The problem statement
            classification: Classification result
            
        Returns:
            Dict with analysis results:
            - needs_diagram: bool
            - diagram_type: str (if needs_diagram)
            - complexity: str (simple, moderate, complex)
            - special_requirements: list[str]
        """
        analysis = {
            "needs_diagram": classification.has_diagram,
            "diagram_type": None,
            "complexity": "moderate",
            "special_requirements": [],
        }
        
        # Determine diagram type from classification
        if classification.has_diagram:
            # Try to get from diagram_type field
            if hasattr(classification, 'diagram_type') and classification.diagram_type:
                analysis["diagram_type"] = classification.diagram_type
            else:
                # Infer from subject
                if self.subject == "physics":
                    analysis["diagram_type"] = "generic"
                elif self.subject == "chemistry":
                    analysis["diagram_type"] = "organic_structure"
                elif self.subject == "mathematics":
                    analysis["diagram_type"] = "function_graph"
        
        # Detect complexity (simple heuristic for now)
        if len(problem_text) > 500:
            analysis["complexity"] = "complex"
        elif len(problem_text) < 200:
            analysis["complexity"] = "simple"
        
        # Detect special requirements
        if "prove" in problem_text.lower() or "show that" in problem_text.lower():
            analysis["special_requirements"].append("proof")
        
        if "derive" in problem_text.lower():
            analysis["special_requirements"].append("derivation")
        
        if "explain" in problem_text.lower():
            analysis["special_requirements"].append("explanation")
        
        return analysis
    
    def route_to_solution_agent(self) -> str:
        """Route to appropriate solution agent based on subject and type.
        
        Returns:
            Agent identifier string (e.g., "physics_subjective")
        """
        # Map question types to agent types
        type_mapping = {
            "subjective": "subjective",
            "mcq_sc": "mcq_sc",
            "mcq_mc": "mcq_mc",
            "assertion_reason": "assertion_reason",
            "match": "match",
            "passage": "passage",
            "integer": "integer",
            "numerical": "numerical",
        }
        
        agent_type = type_mapping.get(self.question_type, "subjective")
        return f"{self.subject}_{agent_type}"
    
    def generate_solution_with_agent(
        self,
        agent_id: str,
        problem_text: str,
        image_path: Optional[str] = None,
        diagram_requirements: Optional[list[DiagramRequirement]] = None,
    ) -> SolutionOutput:
        """Generate solution using the specified agent.
        
        Args:
            agent_id: Agent identifier (e.g., "physics_subjective")
            problem_text: Problem statement
            image_path: Optional path to problem image
            diagram_requirements: Optional diagram requirements from analysis
            
        Returns:
            SolutionOutput with solution and diagram requirements
        """
        # Import the appropriate solution generator
        subject, qtype = agent_id.split("_", 1)
        
        if subject == "physics":
            from vbagent.agents.content_generation.solution.physics import generate_solution
        elif subject == "chemistry":
            from vbagent.agents.content_generation.solution.chemistry import generate_solution
        elif subject == "mathematics":
            from vbagent.agents.content_generation.solution.mathematics import generate_solution
        else:
            raise ValueError(f"Unknown subject: {subject}")
        
        # Generate solution
        solution_output = generate_solution(
            problem_text=problem_text,
            question_type=qtype,
            image_path=image_path,
            use_context=self.use_context,
            show_spinner=self.show_spinner,
        )
        
        return solution_output
    
    def generate_diagrams(
        self,
        diagram_requirements: list[DiagramRequirement],
        image_path: Optional[str] = None,
        problem_text: Optional[str] = None,
        solution_context: Optional[str] = None,
    ) -> dict[str, str]:
        """Generate diagrams based on requirements with rich context.
        
        Phase 2 Enhancement: Extracts subject-specific context from diagram
        requirements and passes it to specialized diagram agents.
        
        Args:
            diagram_requirements: List of diagram requirements
            image_path: Optional path to problem image
            problem_text: Optional problem text for context
            solution_context: Optional solution context
            
        Returns:
            Dict mapping diagram IDs to TikZ code
        """
        from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
        
        diagrams = {}
        
        for req in diagram_requirements:
            # Extract subject-specific context
            subject_context = None
            if self.subject == "physics" and req.physics_context:
                subject_context = req.physics_context
            elif self.subject == "chemistry" and req.chemistry_context:
                subject_context = req.chemistry_context
            elif self.subject == "mathematics" and req.mathematics_context:
                subject_context = req.mathematics_context
            
            # Build enhanced context string
            enhanced_context = req.context
            if subject_context:
                # Append subject-specific context to general context
                context_parts = [enhanced_context]
                for key, value in subject_context.items():
                    if value:
                        context_parts.append(f"{key}: {value}")
                enhanced_context = " | ".join(context_parts)
            
            # Generate TikZ with rich context
            tikz_code, agent_used = generate_tikz_with_routing(
                image_path=image_path,
                description=req.description,
                diagram_type=req.diagram_type,
                subject=self.subject,
                use_context=self.use_context,
                show_spinner=self.show_spinner,
                problem_text=problem_text,
                solution_context=enhanced_context,  # Pass enhanced context
                values={k: str(v) for k, v in req.values.items()} if req.values else None,
                labels=req.labels,
            )
            
            diagrams[req.diagram_id] = tikz_code
        
        return diagrams
    
    def assemble_solution(
        self,
        solution_output: SolutionOutput,
        diagrams: Optional[dict[str, str]] = None,
    ) -> str:
        """Assemble final solution with diagrams inserted.
        
        Args:
            solution_output: Solution output from agent
            diagrams: Optional dict of diagram_id -> tikz_code
            
        Returns:
            Final solution LaTeX with diagrams inserted
        """
        solution_latex = solution_output.solution
        
        # Insert diagrams if present
        if diagrams and solution_output.diagram_requirements:
            for req in solution_output.diagram_requirements:
                if req.diagram_id in diagrams:
                    tikz_code = diagrams[req.diagram_id]
                    
                    # Wrap in center environment
                    tikz_wrapped = f"\\begin{{center}}\n{tikz_code}\n\\end{{center}}"
                    
                    # Replace placeholder
                    placeholder = f"\\input{{{req.diagram_id}}}"
                    solution_latex = solution_latex.replace(placeholder, tikz_wrapped)
        
        return solution_latex
    
    def orchestrate(
        self,
        problem_text: str,
        classification: ClassificationResult,
        image_path: Optional[str] = None,
    ) -> tuple[str, dict]:
        """Main orchestration method - coordinates entire solution generation.
        
        Args:
            problem_text: Problem statement
            classification: Classification result
            image_path: Optional path to problem image
            
        Returns:
            Tuple of (solution_latex, metadata_dict)
        """
        # Step 1: Analyze needs
        analysis = self.analyze_needs(problem_text, classification)
        
        # Step 2: Route to appropriate agent
        agent_id = self.route_to_solution_agent()
        
        # Step 3: Generate solution (may include diagram requirements)
        solution_output = self.generate_solution_with_agent(
            agent_id=agent_id,
            problem_text=problem_text,
            image_path=image_path,
        )
        
        # Step 4: Generate diagrams if needed
        diagrams = None
        if solution_output.diagram_requirements:
            diagrams = self.generate_diagrams(
                diagram_requirements=solution_output.diagram_requirements,
                image_path=image_path,
                problem_text=problem_text,
                solution_context=solution_output.solution,
            )
        
        # Step 5: Assemble final solution
        final_solution = self.assemble_solution(solution_output, diagrams)
        
        # Step 6: Prepare metadata
        metadata = {
            "agent_used": agent_id,
            "analysis": analysis,
            "diagram_count": len(diagrams) if diagrams else 0,
            "has_diagrams": bool(diagrams),
        }
        
        return final_solution, metadata


def generate_solution_orchestrated(
    problem_text: str,
    classification: ClassificationResult,
    subject: str,
    image_path: Optional[str] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> str:
    """Generate solution using orchestrator pattern.
    
    This is the main entry point for orchestrated solution generation.
    
    Args:
        problem_text: Problem statement
        classification: Classification result
        subject: Subject (physics, chemistry, mathematics)
        image_path: Optional path to problem image
        use_context: Whether to use reference context
        show_spinner: Whether to show progress spinners
        
    Returns:
        Solution LaTeX
    """
    orchestrator = SolutionOrchestrator(
        subject=subject,
        question_type=classification.question_type,
        use_context=use_context,
        show_spinner=show_spinner,
    )
    
    solution_latex, metadata = orchestrator.orchestrate(
        problem_text=problem_text,
        classification=classification,
        image_path=image_path,
    )
    
    return solution_latex
