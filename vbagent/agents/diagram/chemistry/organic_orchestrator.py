"""Organic Chemistry Diagram Orchestrator.

Intelligently routes organic chemistry diagram requests to specialized
sub-agents based on diagram type and complexity.
"""

from typing import Optional
import re


class OrganicChemistryOrchestrator:
    """Orchestrates organic chemistry diagram generation with specialized agents.
    
    This orchestrator:
    1. Analyzes diagram requirements (type, complexity, features)
    2. Routes to appropriate specialist agent
    3. Validates output
    4. Handles retry logic with feedback
    """
    
    def __init__(
        self,
        use_context: bool = True,
        show_spinner: bool = True,
    ):
        """Initialize orchestrator.
        
        Args:
            use_context: Whether to use reference context
            show_spinner: Whether to show progress spinners
        """
        self.use_context = use_context
        self.show_spinner = show_spinner
    
    def analyze_diagram_request(
        self,
        description: str,
        chemistry_context: Optional[dict] = None,
        problem_text: Optional[str] = None,
    ) -> dict:
        """Analyze what type of organic diagram is needed.
        
        Args:
            description: Diagram description
            chemistry_context: Subject-specific context from Phase 2
            problem_text: Optional problem text for additional context
            
        Returns:
            Dict with analysis results:
            - diagram_type: str (simple, complex, mechanism, etc.)
            - complexity: str (low, medium, high)
            - features: list[str] (stereochemistry, arrows, etc.)
            - specialist: str (which agent to use)
        """
        analysis = {
            "diagram_type": None,
            "complexity": "medium",
            "features": [],
            "specialist": None,
        }
        
        desc_lower = description.lower()
        
        # Check chemistry_context first (most reliable)
        if chemistry_context:
            if chemistry_context.get("mechanism_step"):
                analysis["diagram_type"] = "mechanism"
                analysis["specialist"] = "mechanism"
                analysis["features"].append("mechanism")
                return analysis
            
            if chemistry_context.get("stereochemistry"):
                analysis["features"].append("stereochemistry")
        
        # Check for FULL mechanism (curved arrows, intermediates, charges)
        full_mechanism_keywords = [
            "curved arrow", "electron movement", "intermediate", "carbocation",
            "carbanion", "nucleophilic attack", "electrophilic attack",
            "resonance", "transition state", "mechanism step", "electron flow"
        ]
        if any(word in desc_lower for word in full_mechanism_keywords):
            analysis["diagram_type"] = "mechanism"
            analysis["specialist"] = "mechanism"
            analysis["features"].append("mechanism")
            return analysis
        
        # Check for reaction scheme (just reactant → product, no mechanism details)
        # BUT if description mentions "mechanism" without the detailed keywords above,
        # it might be misclassified - default to simple structure for safety
        reaction_scheme_keywords = [
            "reaction scheme", "product", "reagent", "starting material",
            "identify the product", "following reaction", "excess", "reactant"
        ]
        mechanism_without_details = "mechanism" in desc_lower and not any(word in desc_lower for word in full_mechanism_keywords)
        
        if any(word in desc_lower for word in reaction_scheme_keywords) or mechanism_without_details:
            # This is likely a reaction scheme or misclassified mechanism
            # Use simple_molecule specialist for safety
            if "transform" in desc_lower or "change" in desc_lower:
                analysis["diagram_type"] = "transformation"
                analysis["specialist"] = "functional_group"
            else:
                analysis["diagram_type"] = "reaction_scheme"
                analysis["specialist"] = "simple_molecule"
            analysis["features"].append("reaction_scheme")
            return analysis
        
        # Check for multi-step synthesis
        synthesis_keywords = [
            "synthesis", "steps", "sequence", "pathway",
            "multi-step", "retrosynthesis"
        ]
        if any(word in desc_lower for word in synthesis_keywords):
            analysis["diagram_type"] = "multi_step"
            analysis["specialist"] = "multi_step"
            analysis["features"].append("multi_step")
            return analysis
        
        # Check for stereochemistry focus
        stereo_keywords = [
            "stereochemistry", "chiral", "r/s", "e/z", "wedge", "dash",
            "configuration", "enantiomer", "diastereomer", "fischer",
            "chair", "boat", "conformation"
        ]
        if any(word in desc_lower for word in stereo_keywords):
            analysis["diagram_type"] = "stereochemistry"
            analysis["specialist"] = "stereochemistry"
            analysis["features"].append("stereochemistry")
            return analysis
        
        # Check for transformation/functional group change
        transform_keywords = [
            "transform", "oxidation", "reduction", "convert",
            "protection", "deprotection", "substitution"
        ]
        if any(word in desc_lower for word in transform_keywords):
            analysis["diagram_type"] = "transformation"
            analysis["specialist"] = "functional_group"
            analysis["features"].append("transformation")
            return analysis
        
        # Default: structure (simple or complex)
        # Determine complexity
        complex_keywords = [
            "steroid", "alkaloid", "natural product", "polycyclic",
            "fused ring", "bridged", "terpene", "peptide", "oligosaccharide"
        ]
        
        if any(word in desc_lower for word in complex_keywords):
            analysis["diagram_type"] = "complex_molecule"
            analysis["specialist"] = "complex_molecule"
            analysis["complexity"] = "high"
        else:
            analysis["diagram_type"] = "simple_molecule"
            analysis["specialist"] = "simple_molecule"
            analysis["complexity"] = "low"
        
        return analysis
    
    def route_to_specialist(
        self,
        specialist: str,
        image_path: Optional[str] = None,
        description: Optional[str] = None,
        chemistry_context: Optional[dict] = None,
        problem_text: Optional[str] = None,
        mcq_options: bool = False,
    ) -> str:
        """Route to appropriate specialist agent.
        
        Args:
            specialist: Specialist identifier
            image_path: Optional path to image
            description: Optional text description
            chemistry_context: Subject-specific context
            problem_text: Optional problem text
            mcq_options: Whether generating MCQ options
            
        Returns:
            ChemFig code
        """
        
        if specialist == "simple_molecule":
            from vbagent.agents.diagram.chemistry.organic_simple import (
                generate_simple_molecule
            )
            return generate_simple_molecule(
                image_path=image_path,
                description=description,
                chemistry_context=chemistry_context,
                use_context=self.use_context,
                show_spinner=self.show_spinner,
                mcq_options=mcq_options,
            )
        
        elif specialist == "mechanism":
            from vbagent.agents.diagram.chemistry.organic_mechanism import (
                generate_mechanism
            )
            return generate_mechanism(
                image_path=image_path,
                description=description,
                chemistry_context=chemistry_context,
                problem_text=problem_text,
                use_context=self.use_context,
                show_spinner=self.show_spinner,
            )
        
        elif specialist == "stereochemistry":
            from vbagent.agents.diagram.chemistry.organic_stereo import (
                generate_stereochemistry
            )
            return generate_stereochemistry(
                image_path=image_path,
                description=description,
                chemistry_context=chemistry_context,
                use_context=self.use_context,
                show_spinner=self.show_spinner,
                mcq_options=mcq_options,
            )
        
        elif specialist == "complex_molecule":
            from vbagent.agents.diagram.chemistry.organic_complex import (
                generate_complex_molecule
            )
            return generate_complex_molecule(
                image_path=image_path,
                description=description,
                chemistry_context=chemistry_context,
                use_context=self.use_context,
                show_spinner=self.show_spinner,
            )
        
        elif specialist == "functional_group":
            from vbagent.agents.diagram.chemistry.organic_functional import (
                generate_functional_group_transformation
            )
            return generate_functional_group_transformation(
                image_path=image_path,
                description=description,
                chemistry_context=chemistry_context,
                use_context=self.use_context,
                show_spinner=self.show_spinner,
            )
        
        elif specialist == "multi_step":
            from vbagent.agents.diagram.chemistry.organic_multistep import (
                generate_multi_step_synthesis
            )
            return generate_multi_step_synthesis(
                image_path=image_path,
                description=description,
                chemistry_context=chemistry_context,
                use_context=self.use_context,
                show_spinner=self.show_spinner,
            )
        
        else:
            # Fallback to general organic structure agent
            from vbagent.agents.diagram.chemistry.organic_structure import (
                generate_organic_structure
            )
            return generate_organic_structure(
                image_path=image_path,
                description=description,
                use_context=self.use_context,
                show_spinner=self.show_spinner,
                mcq_options=mcq_options,
            )
    
    def validate_chemfig_output(
        self,
        chemfig_code: str,
        diagram_type: str,
    ) -> tuple[bool, list[str]]:
        """Validate ChemFig code for common issues.
        
        Args:
            chemfig_code: The ChemFig code to validate
            diagram_type: Type of diagram for type-specific validation
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        if not chemfig_code or not chemfig_code.strip():
            issues.append("Empty ChemFig code")
            return False, issues
        
        # Check for balanced braces (only critical errors)
        brace_diff = chemfig_code.count("{") - chemfig_code.count("}")
        if abs(brace_diff) > 2:  # Allow small imbalance (might be in comments)
            issues.append(f"Unbalanced braces (diff: {brace_diff})")
        
        # Check for chemfig command or option definitions
        has_chemfig = "\\chemfig{" in chemfig_code or "\\chemfig " in chemfig_code
        has_options = "\\def\\Option" in chemfig_code
        has_scheme = "\\schemestart" in chemfig_code or "\\arrow" in chemfig_code
        
        if not (has_chemfig or has_options or has_scheme):
            issues.append("Missing \\chemfig{} command or \\def\\Option definitions")
        
        # Relaxed validation - only fail on critical issues
        critical_issues = [issue for issue in issues if "Empty" in issue or "Missing" in issue]
        
        return len(critical_issues) == 0, issues
    
    def generate_with_retry(
        self,
        specialist: str,
        image_path: Optional[str] = None,
        description: Optional[str] = None,
        chemistry_context: Optional[dict] = None,
        problem_text: Optional[str] = None,
        mcq_options: bool = False,
        max_retries: int = 1,  # Reduced from 2 to 1 for better performance
    ) -> str:
        """Generate with validation and retry.
        
        Args:
            specialist: Specialist identifier
            image_path: Optional path to image
            description: Optional text description
            chemistry_context: Subject-specific context
            problem_text: Optional problem text
            mcq_options: Whether generating MCQ options
            max_retries: Maximum number of retries
            
        Returns:
            ChemFig code
        """
        last_chemfig_code = None
        
        for attempt in range(max_retries + 1):
            chemfig_code = self.route_to_specialist(
                specialist=specialist,
                image_path=image_path,
                description=description,
                chemistry_context=chemistry_context,
                problem_text=problem_text,
                mcq_options=mcq_options,
            )
            
            last_chemfig_code = chemfig_code
            
            valid, issues = self.validate_chemfig_output(
                chemfig_code, specialist
            )
            
            if valid:
                return chemfig_code
            
            # If validation fails and we have retries left, try fallback specialist
            if attempt < max_retries:
                # Add issues to context for retry
                if chemistry_context is None:
                    chemistry_context = {}
                chemistry_context["previous_issues"] = issues
                
                # Try fallback specialist on last retry
                if attempt == max_retries - 1:
                    # Fallback logic: try simpler specialist
                    if specialist == "mechanism":
                        specialist = "simple_molecule"
                    elif specialist == "complex_molecule":
                        specialist = "simple_molecule"
                    elif specialist == "multi_step":
                        specialist = "functional_group"
        
        # Final fallback - return best attempt even if validation failed
        return last_chemfig_code
    
    def orchestrate(
        self,
        image_path: Optional[str] = None,
        description: Optional[str] = None,
        chemistry_context: Optional[dict] = None,
        problem_text: Optional[str] = None,
        mcq_options: bool = False,
    ) -> tuple[str, dict]:
        """Main orchestration method - coordinates entire diagram generation.
        
        Args:
            image_path: Optional path to image
            description: Optional text description
            chemistry_context: Subject-specific context from Phase 2
            problem_text: Optional problem text
            mcq_options: Whether generating MCQ options
            
        Returns:
            Tuple of (chemfig_code, metadata_dict)
        """
        # Step 1: Analyze diagram requirements
        analysis = self.analyze_diagram_request(
            description=description or "",
            chemistry_context=chemistry_context,
            problem_text=problem_text,
        )
        
        # Step 2: Generate with retry
        chemfig_code = self.generate_with_retry(
            specialist=analysis["specialist"],
            image_path=image_path,
            description=description,
            chemistry_context=chemistry_context,
            problem_text=problem_text,
            mcq_options=mcq_options,
        )
        
        # Step 3: Prepare metadata
        metadata = {
            "specialist_used": analysis["specialist"],
            "diagram_type": analysis["diagram_type"],
            "complexity": analysis["complexity"],
            "features": analysis["features"],
        }
        
        return chemfig_code, metadata


def generate_organic_orchestrated(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    chemistry_context: Optional[dict] = None,
    problem_text: Optional[str] = None,
    use_context: bool = True,
    show_spinner: bool = True,
    mcq_options: bool = False,
) -> str:
    """Generate organic chemistry diagram using orchestrator pattern.
    
    This is the main entry point for orchestrated organic diagram generation.
    
    Args:
        image_path: Optional path to image
        description: Optional text description
        chemistry_context: Subject-specific context from Phase 2
        problem_text: Optional problem text
        use_context: Whether to use reference context
        show_spinner: Whether to show progress spinners
        mcq_options: Whether generating MCQ options
        
    Returns:
        ChemFig code
    """
    orchestrator = OrganicChemistryOrchestrator(
        use_context=use_context,
        show_spinner=show_spinner,
    )
    
    chemfig_code, metadata = orchestrator.orchestrate(
        image_path=image_path,
        description=description,
        chemistry_context=chemistry_context,
        problem_text=problem_text,
        mcq_options=mcq_options,
    )
    
    return chemfig_code
