"""Variant agents for physics problem generation.

Uses openai-agents SDK to generate different types of problem variants:
- numerical: Modify only numerical values
- context: Modify only the scenario/context
- conceptual: Modify the core physics concept
- calculus: Add calculus-based modifications
"""

from typing import Any, Optional

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.models.content import IdeaResult
from vbagent.prompts.variants.conceptual import (
    SYSTEM_PROMPT as CONCEPTUAL_SYSTEM_PROMPT,
)
from vbagent.prompts.variants.conceptual import (
    USER_TEMPLATE as CONCEPTUAL_USER_TEMPLATE,
)
from vbagent.prompts.variants.conceptual_calculus import (
    SYSTEM_PROMPT as CALCULUS_SYSTEM_PROMPT,
)
from vbagent.prompts.variants.conceptual_calculus import (
    USER_TEMPLATE as CALCULUS_USER_TEMPLATE,
)
from vbagent.prompts.variants.context import (
    SYSTEM_PROMPT as CONTEXT_SYSTEM_PROMPT,
)
from vbagent.prompts.variants.context import (
    USER_TEMPLATE as CONTEXT_USER_TEMPLATE,
)
from vbagent.prompts.variants.numerical import (
    SYSTEM_PROMPT as NUMERICAL_SYSTEM_PROMPT,
)
from vbagent.prompts.variants.numerical import (
    USER_TEMPLATE as NUMERICAL_USER_TEMPLATE,
)
from vbagent.references.context import get_context_prompt_section
from vbagent.utils.latex import clean_latex_output

# Mapping of variant types to their prompts
VARIANT_PROMPTS = {
    "numerical": {
        "system": NUMERICAL_SYSTEM_PROMPT,
        "user": NUMERICAL_USER_TEMPLATE,
    },
    "context": {
        "system": CONTEXT_SYSTEM_PROMPT,
        "user": CONTEXT_USER_TEMPLATE,
    },
    "conceptual": {
        "system": CONCEPTUAL_SYSTEM_PROMPT,
        "user": CONCEPTUAL_USER_TEMPLATE,
    },
    "calculus": {
        "system": CALCULUS_SYSTEM_PROMPT,
        "user": CALCULUS_USER_TEMPLATE,
    },
}

# Standard variant types (single-agent, use VARIANT_PROMPTS)
STANDARD_VARIANT_TYPES = list(VARIANT_PROMPTS.keys())

# All valid variant types (includes multi-stage pipelines)
VALID_VARIANT_TYPES = STANDARD_VARIANT_TYPES + ["cross_topic"]


def get_variant_prompt(variant_type: str) -> tuple[str, str]:
    """Get the system and user prompts for a standard variant type.
    
    Args:
        variant_type: Type of variant (numerical, context, conceptual, calculus)
        
    Returns:
        Tuple of (system_prompt, user_template)
        
    Raises:
        ValueError: If variant_type is not a standard prompt-based type
    """
    if variant_type not in VARIANT_PROMPTS:
        raise ValueError(
            f"Invalid variant type: {variant_type}. "
            f"Valid types are: {STANDARD_VARIANT_TYPES}"
        )
    
    prompts = VARIANT_PROMPTS[variant_type]
    return prompts["system"], prompts["user"]


def create_variant_agent(variant_type: str, use_context: bool = True):
    """Create a variant agent with type-specific prompt.
    
    Args:
        variant_type: Type of variant (numerical, context, conceptual, calculus)
        use_context: Whether to include reference context in prompt
        
    Returns:
        Configured Agent instance for the variant type
        
    Raises:
        ValueError: If variant_type is not valid
    """
    system_prompt, _ = get_variant_prompt(variant_type)
    
    # Add reference context if enabled
    context = get_context_prompt_section("variants", use_context)
    if context:
        system_prompt = system_prompt + "\n" + context

    system_prompt += (
        "\n\nComponent selection: an explicit include_solution/include_idea "
        "request overrides the default output format above. If a component is "
        "false, do not generate it or hide it in comments or another component. "
        "The question and its answer markers are always required. An idea, when "
        "requested, is a concise conceptual hint in an idea environment, not a worked solution."
    )
    
    return create_agent(
        name=f"Variant-{variant_type}",
        instructions=system_prompt,
        agent_type="variant",
    )


def generate_variant(
    source_latex: str,
    variant_type: str,
    ideas: Optional[IdeaResult] = None,
    use_context: bool = True,
    classification: Optional[Any] = None,
    *,
    include_solution: bool = True,
    include_idea: bool = False,
) -> str:
    """Generate a variant of the source problem.
    
    Creates a new problem variant based on the specified type:
    - numerical: Changes only numerical values
    - context: Changes only the scenario/context
    - conceptual: Changes the core physics concept
    - calculus: Adds calculus-based modifications
    - cross_topic: Integrates a complementary physics topic (multi-stage)
    
    Args:
        source_latex: The source problem in LaTeX format
        variant_type: Type of variant to generate
        ideas: Optional IdeaResult with extracted concepts (used for context)
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for cross_topic variants
        include_solution: Include a worked solution now, or defer it
        include_idea: Include a concise conceptual idea after the question/solution
        
    Returns:
        The generated variant in LaTeX format
        
    Raises:
        ValueError: If source_latex is empty or variant_type is invalid
    """
    if not source_latex.strip():
        raise ValueError("Source LaTeX cannot be empty")
    
    # Cross-topic uses its own multi-stage pipeline
    if variant_type == "cross_topic":
        if not include_solution or include_idea:
            raise ValueError("component selection is supported for standard variants only")
        from .cross_topic import analyze_cross_topic, generate_cross_topic_variant
        
        # Extract classification info if available
        subject = "physics"
        topic = None
        question_type = "subjective"
        has_diagram = False
        key_concepts = None
        
        if classification:
            subject = getattr(classification, 'subject', 'physics')
            topic = getattr(classification, 'topic', None)
            question_type = getattr(classification, 'question_type', 'subjective')
            has_diagram = getattr(classification, 'has_diagram', False)
            key_concepts = getattr(classification, 'key_concepts', None)
        
        if ideas and ideas.concepts:
            key_concepts = key_concepts or []
            key_concepts = list(set(key_concepts + ideas.concepts))
        
        # Stage 1: Analyze and pick integration topic
        analysis = analyze_cross_topic(
            source_latex=source_latex,
            subject=subject,
            topic=topic,
            question_type=question_type,
            has_diagram=has_diagram,
            key_concepts=key_concepts,
        )
        
        # Stage 2: Generate the cross-topic variant
        return generate_cross_topic_variant(
            source_latex=source_latex,
            analysis=analysis,
            use_context=use_context,
        )
    
    # Standard single-agent variant types
    # Get prompts for this variant type
    system_prompt, user_template = get_variant_prompt(variant_type)
    
    # Create the agent
    agent = create_variant_agent(variant_type, use_context)
    
    # Format the user message
    message = user_template.format(source_latex=source_latex)
    message += (
        f"\n\nComponent selection: include_solution={str(include_solution).lower()}, "
        f"include_idea={str(include_idea).lower()}. "
        "Return the question followed only by the selected components. "
        "When solutions are deferred, do not produce a worked derivation or an alternate solution."
    )
    
    # Add ideas context if provided
    if ideas and ideas.concepts:
        message += f"\n\nKey Concepts: {', '.join(ideas.concepts)}"
    if ideas and ideas.techniques:
        message += f"\nTechniques: {', '.join(ideas.techniques)}"
    
    # Run the agent
    raw_result = run_agent_sync(agent, message)
    
    # Clean up markdown artifacts from LLM output
    return clean_latex_output(raw_result)


# Convenience functions for specific variant types

def generate_numerical_variant(
    source_latex: str,
    ideas: Optional[IdeaResult] = None,
    use_context: bool = True,
) -> str:
    """Generate a numerical variant (changes only numerical values).
    
    Args:
        source_latex: The source problem in LaTeX format
        ideas: Optional IdeaResult with extracted concepts
        use_context: Whether to include reference context in prompt
        
    Returns:
        The generated variant in LaTeX format
    """
    return generate_variant(source_latex, "numerical", ideas, use_context)


def generate_context_variant(
    source_latex: str,
    ideas: Optional[IdeaResult] = None,
    use_context: bool = True,
) -> str:
    """Generate a context variant (changes only the scenario/context).
    
    Args:
        source_latex: The source problem in LaTeX format
        ideas: Optional IdeaResult with extracted concepts
        use_context: Whether to include reference context in prompt
        
    Returns:
        The generated variant in LaTeX format
    """
    return generate_variant(source_latex, "context", ideas, use_context)


def generate_conceptual_variant(
    source_latex: str,
    ideas: Optional[IdeaResult] = None,
    use_context: bool = True,
) -> str:
    """Generate a conceptual variant (changes the core physics concept).
    
    Args:
        source_latex: The source problem in LaTeX format
        ideas: Optional IdeaResult with extracted concepts
        use_context: Whether to include reference context in prompt
        
    Returns:
        The generated variant in LaTeX format
    """
    return generate_variant(source_latex, "conceptual", ideas, use_context)


def generate_calculus_variant(
    source_latex: str,
    ideas: Optional[IdeaResult] = None,
    use_context: bool = True,
) -> str:
    """Generate a calculus variant (adds calculus-based modifications).
    
    Args:
        source_latex: The source problem in LaTeX format
        ideas: Optional IdeaResult with extracted concepts
        use_context: Whether to include reference context in prompt
        
    Returns:
        The generated variant in LaTeX format
    """
    return generate_variant(source_latex, "calculus", ideas, use_context)
