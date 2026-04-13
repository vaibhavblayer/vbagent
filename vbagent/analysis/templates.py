"""Template loading and management for chapter analysis."""

import json
from pathlib import Path
from typing import Optional


def load_chapter_template(exam: str, subject: str, chapter_name: str) -> Optional[dict]:
    """Load the template for a specific chapter.
    
    Args:
        exam: Exam type (e.g., 'jee_main', 'neet')
        subject: Subject name (e.g., 'physics')
        chapter_name: Chapter name (e.g., 'WORK, ENERGY, AND POWER')
        
    Returns:
        Template dictionary or None if not found
    """
    # Sanitize chapter name to filename
    filename = chapter_name.lower().replace(' ', '_').replace(',', '').replace('/', '_') + '.json'
    
    # Build path
    template_path = Path(__file__).parent.parent / 'data' / 'templates' / exam / subject / filename
    
    if not template_path.exists():
        return None
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def get_template_concepts(template: dict) -> list[dict]:
    """Extract all concepts from template organized by topic.
    
    Args:
        template: Template dictionary
        
    Returns:
        List of dicts with topic_name and items (concepts/formulas/techniques)
    """
    if not template:
        return []
    
    result = []
    for topic in template.get('topics', []):
        topic_data = {
            'topic_name': topic['topic_name'],
            'concepts': topic.get('concepts', []),
            'formulas': topic.get('formulas', []),
            'techniques': topic.get('techniques', [])
        }
        result.append(topic_data)
    
    return result


def format_template_for_agent(template: dict) -> str:
    """Format template data for agent input.
    
    Args:
        template: Template dictionary
        
    Returns:
        Formatted string for agent prompt
    """
    if not template:
        return "(No template available for this chapter)\n"
    
    output = f"# Standard Concepts for {template['chapter']}\n\n"
    
    # Add conceptual note if available
    if template.get('note'):
        output += "## Conceptual Framework\n\n"
        output += f"{template['note']}\n\n"
    
    for topic in template.get('topics', []):
        topic_name = topic['topic_name']
        concepts = topic.get('concepts', [])
        formulas = topic.get('formulas', [])
        techniques = topic.get('techniques', [])
        
        # Skip empty topics
        if not concepts and not formulas and not techniques:
            continue
        
        output += f"## {topic_name}\n\n"
        
        if concepts:
            output += "**Standard Concepts:**\n"
            for concept in concepts:
                output += f"- {concept}\n"
            output += "\n"
        
        if formulas:
            output += "**Standard Formulas:**\n"
            for formula in formulas:
                if isinstance(formula, dict):
                    latex = formula.get('latex', '')
                    desc = formula.get('description', '')
                    output += f"- ${latex}$ --- {desc}\n"
                else:
                    output += f"- {formula}\n"
            output += "\n"
        
        if techniques:
            output += "**Standard Techniques:**\n"
            for technique in techniques:
                output += f"- {technique}\n"
            output += "\n"
    
    return output
