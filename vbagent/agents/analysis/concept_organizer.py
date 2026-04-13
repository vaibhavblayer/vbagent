"""Agent for organizing and deduplicating concepts from multiple problems."""

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agent

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.analysis.concept_organizer import get_concept_organizer_prompt


def _get_cache_key(raw_ideas: dict, syllabus_topics: list[str], chapter_name: str) -> str:
    """Generate a cache key based on input data."""
    # Create a deterministic string from inputs
    cache_data = {
        'chapter': chapter_name,
        'topics': syllabus_topics,
        'ideas': raw_ideas
    }
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_str.encode()).hexdigest()


def _get_cache_path(cache_key: str) -> Path:
    """Get the cache file path for a given key."""
    cache_dir = Path('.vbagent/cache/analysis')
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{cache_key}.json"


def _load_from_cache(cache_key: str) -> dict | None:
    """Load organized concepts from cache."""
    cache_path = _get_cache_path(cache_key)
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _save_to_cache(cache_key: str, data: dict):
    """Save organized concepts to cache."""
    cache_path = _get_cache_path(cache_key)
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass  # Silently fail if cache write fails


def organize_concepts(
    raw_ideas: dict,
    syllabus_topics: list[str],
    chapter_name: str,
    exam: str = 'jee_main',
    subject: str = 'physics',
    show_spinner: bool = True,
    no_cache: bool = False,
) -> dict:
    """Organize and deduplicate concepts from multiple problems.
    
    Uses an AI agent to intelligently:
    - Deduplicate similar concepts
    - Group related ideas
    - Format for LaTeX output
    - Identify key formulas and techniques
    - Cross-reference with standard chapter templates
    
    Args:
        raw_ideas: Dictionary with raw extracted ideas from all problems
        syllabus_topics: List of syllabus topics for this chapter
        chapter_name: Name of the chapter being analyzed
        exam: Exam type (e.g., 'jee_main', 'neet')
        subject: Subject name (e.g., 'physics')
        show_spinner: Whether to show progress spinner
        no_cache: If True, force regeneration without using cache
        
    Returns:
        Organized structure ready for LaTeX generation
    """
    from vbagent.agents.analysis.models import OrganizedConcepts
    
    # Check cache first (unless no_cache is True)
    if not no_cache:
        cache_key = _get_cache_key(raw_ideas, syllabus_topics, chapter_name)
        cached_result = _load_from_cache(cache_key)
        if cached_result:
            return cached_result
    
    # Build input for agent (includes full problems + template)
    agent_input = _build_agent_input(raw_ideas, syllabus_topics, chapter_name, exam, subject)
    
    # Create agent
    agent = create_agent(
        name="ConceptOrganizer",
        instructions=get_concept_organizer_prompt(),
        output_type=OrganizedConcepts,
        agent_type="idea",
    )
    
    # Run agent (note: no_cache parameter reserved for future cache implementation)
    result = run_agent_sync(agent, agent_input, show_spinner=show_spinner)
    
    # Convert to dictionary format
    organized = _convert_to_dict(result)
    
    # Save to cache
    if not no_cache:
        cache_key = _get_cache_key(raw_ideas, syllabus_topics, chapter_name)
        _save_to_cache(cache_key, organized)
    
    return organized


def _build_agent_input(raw_ideas: dict, syllabus_topics: list[str], chapter_name: str, exam: str, subject: str) -> str:
    """Build formatted input for the agent with full problems and templates."""
    from vbagent.analysis.templates import load_chapter_template, format_template_for_agent
    
    input_text = f"""# Chapter: {chapter_name}

## Syllabus Topics
"""
    
    for i, topic in enumerate(syllabus_topics, 1):
        input_text += f"{i}. {topic}\n"
    
    # Load and add template if available
    template = load_chapter_template(exam, subject, chapter_name)
    if template:
        input_text += "\n" + format_template_for_agent(template)
    
    input_text += "\n## Problems from Exam\n\n"
    
    # Extract all problems data (they come under 'all_problems' key now)
    all_problems_data = raw_ideas.get('all_problems', {})
    problems_list = all_problems_data.get('problems', [])
    
    if not problems_list:
        input_text += "(No problems found)\n"
        return input_text
    
    # Add full problem content for each problem
    for problem in problems_list:
        problem_num = problem['problem_num']
        input_text += f"### Problem {problem_num}\n\n"
        
        # Add question
        if problem.get('question'):
            input_text += "**Question:**\n"
            input_text += f"{problem['question']}\n\n"
        
        # Add solution
        if problem.get('solution'):
            input_text += "**Solution:**\n"
            input_text += f"{problem['solution']}\n\n"
        
        # Add extracted ideas
        if problem.get('concepts') or problem.get('formulas') or problem.get('techniques'):
            input_text += "**Extracted Ideas:**\n"
            
            if problem.get('concepts'):
                input_text += "Concepts:\n"
                for concept in problem['concepts']:
                    input_text += f"- {concept}\n"
                input_text += "\n"
            
            if problem.get('formulas'):
                input_text += "Formulas:\n"
                for formula in problem['formulas']:
                    input_text += f"- {formula}\n"
                input_text += "\n"
            
            if problem.get('techniques'):
                input_text += "Techniques:\n"
                for technique in problem['techniques']:
                    input_text += f"- {technique}\n"
                input_text += "\n"
        
        input_text += "---\n\n"
    
    return input_text


def _convert_to_dict(result: "OrganizedConcepts") -> dict:
    """Convert Pydantic model to dictionary format."""
    organized = {}
    
    for topic in result.topics:
        organized[topic.topic_name] = {
            'concepts': [
                {
                    'text': c.text,
                    'problems': c.problem_numbers,
                    'sub_items': c.sub_items if hasattr(c, 'sub_items') else []
                }
                for c in topic.concepts
            ],
            'formulas': [
                {
                    'latex': f.latex,
                    'description': f.description,
                    'problems': f.problem_numbers
                }
                for f in topic.formulas
            ],
            'techniques': [
                {
                    'text': t.text,
                    'problems': t.problem_numbers,
                    'sub_items': t.sub_items if hasattr(t, 'sub_items') else []
                }
                for t in topic.techniques
            ]
        }
    
    return organized
