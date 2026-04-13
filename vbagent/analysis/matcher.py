"""Match problems to syllabus topics and aggregate data."""

import json
from pathlib import Path
from typing import Optional


def load_syllabus(exam: str, subject: str) -> dict:
    """Load syllabus JSON file for an exam and subject.
    
    Args:
        exam: Exam name (jee_main, neet, jee_advanced)
        subject: Subject name (physics, chemistry, mathematics, biology)
        
    Returns:
        Syllabus dictionary
    """
    syllabus_file = Path(__file__).parent.parent / 'data' / 'syllabus' / exam / f'{subject}.json'
    
    if not syllabus_file.exists():
        raise FileNotFoundError(f"Syllabus file not found: {syllabus_file}")
    
    with open(syllabus_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def match_problems_to_syllabus(problems: list[dict], syllabus: dict, chapter_filter: Optional[str] = None) -> dict:
    """Match problems to syllabus topics and create mapping.
    
    Args:
        problems: List of problem data dictionaries
        syllabus: Syllabus dictionary
        chapter_filter: Optional chapter name to filter by
        
    Returns:
        Dictionary mapping:
        {
            'chapter_name': {
                'topics': [
                    {
                        'topic': str,
                        'problems': [1, 5, 12],
                        'ideas': [...]
                    }
                ],
                'all_problems': [1, 2, 3, ...],
                'description': str
            }
        }
    """
    result = {}
    
    # Filter syllabus by chapter if specified
    chapters_to_process = {}
    if chapter_filter:
        # Normalize chapter name (case-insensitive, handle variations)
        chapter_filter_upper = chapter_filter.upper()
        for chapter_name in syllabus:
            if chapter_filter_upper in chapter_name.upper() or chapter_name.upper() in chapter_filter_upper:
                chapters_to_process[chapter_name] = syllabus[chapter_name]
    else:
        chapters_to_process = syllabus
    
    # Process each chapter
    for chapter_name, chapter_data in chapters_to_process.items():
        chapter_result = {
            'topics': [],
            'all_problems': [],
            'description': chapter_data.get('description', ''),
            'problems_data': []
        }
        
        # Find problems matching this chapter
        matching_problems = []
        for problem in problems:
            if _matches_chapter(problem, chapter_name):
                matching_problems.append(problem)
                chapter_result['all_problems'].append(problem['number'])
        
        # For each syllabus topic, find matching problems
        for topic_text in chapter_data.get('topics', []):
            topic_result = {
                'topic': topic_text,
                'problems': [],
                'ideas': []
            }
            
            # Find problems that match this specific topic
            for problem in matching_problems:
                if _matches_topic(problem, topic_text):
                    topic_result['problems'].append(problem['number'])
                    if problem['ideas']:
                        topic_result['ideas'].append({
                            'problem_num': problem['number'],
                            'concepts': problem['ideas'].get('concepts', []),
                            'formulas': problem['ideas'].get('formulas', []),
                            'techniques': problem['ideas'].get('techniques', [])
                        })
            
            chapter_result['topics'].append(topic_result)
        
        # Store all problem data for this chapter
        chapter_result['problems_data'] = matching_problems
        
        result[chapter_name] = chapter_result
    
    return result


def _matches_chapter(problem: dict, chapter_name: str) -> bool:
    """Check if a problem matches a chapter.
    
    Args:
        problem: Problem data dictionary
        chapter_name: Chapter name from syllabus
        
    Returns:
        True if problem belongs to this chapter
    """
    problem_chapter = problem.get('chapter', '').upper()
    chapter_name_upper = chapter_name.upper()
    
    # If problem has no chapter metadata, match all (let user filter manually)
    if not problem_chapter or problem_chapter == 'UNKNOWN':
        return True
    
    # Direct match
    if problem_chapter == chapter_name_upper:
        return True
    
    # Partial match (e.g., "KINEMATICS" in "KINEMATICS AND MOTION")
    if problem_chapter and chapter_name_upper in problem_chapter:
        return True
    
    if chapter_name_upper and problem_chapter in chapter_name_upper:
        return True
    
    # Keyword matching for common variations
    chapter_keywords = _extract_keywords(chapter_name)
    problem_keywords = _extract_keywords(problem_chapter)
    
    # If at least 50% of keywords match
    if chapter_keywords and problem_keywords:
        matches = len(chapter_keywords & problem_keywords)
        if matches / len(chapter_keywords) >= 0.5:
            return True
    
    return False


def _matches_topic(problem: dict, topic_text: str) -> bool:
    """Check if a problem matches a specific topic.
    
    Args:
        problem: Problem data dictionary
        topic_text: Topic text from syllabus
        
    Returns:
        True if problem covers this topic
    """
    # Check problem topic/subtopic metadata
    problem_topic = problem.get('topic', '').lower()
    problem_subtopic = problem.get('subtopic', '').lower()
    topic_lower = topic_text.lower()
    
    # If no topic metadata, match based on ideas content
    if not problem_topic or problem_topic == 'unknown':
        # Check in problem content/ideas for topic keywords
        if problem.get('ideas'):
            ideas_text = problem['ideas'].get('raw', '').lower()
            # Check if topic keywords appear in ideas
            topic_keywords = _extract_keywords(topic_text)
            for keyword in topic_keywords:
                if len(keyword) > 4 and keyword in ideas_text:  # Only check meaningful keywords
                    return True
        # Default to True to include all problems (let agent organize them)
        return True
    
    # Direct match
    if topic_lower in problem_topic or topic_lower in problem_subtopic:
        return True
    
    # Keyword matching
    topic_keywords = _extract_keywords(topic_text)
    problem_keywords = _extract_keywords(problem_topic + ' ' + problem_subtopic)
    
    # If any significant keywords match
    if topic_keywords and problem_keywords:
        matches = len(topic_keywords & problem_keywords)
        if matches > 0:
            return True
    
    # Check in problem content/ideas for topic keywords
    if problem.get('ideas'):
        ideas_text = problem['ideas'].get('raw', '').lower()
        # Check if topic keywords appear in ideas
        for keyword in topic_keywords:
            if len(keyword) > 4 and keyword in ideas_text:  # Only check meaningful keywords
                return True
    
    return False


def _extract_keywords(text: str) -> set:
    """Extract meaningful keywords from text.
    
    Args:
        text: Input text
        
    Returns:
        Set of lowercase keywords
    """
    if not text:
        return set()
    
    # Remove common words
    stop_words = {
        'and', 'or', 'the', 'a', 'an', 'of', 'in', 'to', 'for', 'with', 'on', 'at',
        'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'its', 'their', 'this', 'that', 'these', 'those'
    }
    
    # Split and clean
    words = text.lower().split()
    keywords = set()
    
    for word in words:
        # Remove punctuation
        word = ''.join(c for c in word if c.isalnum())
        # Keep words longer than 3 characters and not stop words
        if len(word) > 3 and word not in stop_words:
            keywords.add(word)
    
    return keywords


def aggregate_ideas_by_topic(matched_data: dict) -> dict:
    """Aggregate and organize ideas by topic across all problems.
    
    Args:
        matched_data: Output from match_problems_to_syllabus
        
    Returns:
        Organized structure for LaTeX generation
    """
    aggregated = {}
    
    for chapter_name, chapter_data in matched_data.items():
        chapter_ideas = {
            'topics': []
        }
        
        for topic_data in chapter_data['topics']:
            if not topic_data['problems']:
                continue  # Skip topics with no problems
            
            # Collect all concepts, formulas, techniques for this topic
            all_concepts = []
            all_formulas = []
            all_techniques = []
            
            for idea in topic_data['ideas']:
                all_concepts.extend(idea['concepts'])
                all_formulas.extend(idea['formulas'])
                all_techniques.extend(idea['techniques'])
            
            # Deduplicate while preserving order
            unique_concepts = list(dict.fromkeys(all_concepts))
            unique_formulas = list(dict.fromkeys(all_formulas))
            unique_techniques = list(dict.fromkeys(all_techniques))
            
            chapter_ideas['topics'].append({
                'topic': topic_data['topic'],
                'problems': topic_data['problems'],
                'concepts': unique_concepts,
                'formulas': unique_formulas,
                'techniques': unique_techniques
            })
        
        aggregated[chapter_name] = chapter_ideas
    
    return aggregated
