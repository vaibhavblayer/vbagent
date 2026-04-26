"""Extract problem data, ideas, and metadata from LaTeX files."""

import re
from pathlib import Path
from typing import Optional


def extract_problem_data(problem_file: Path) -> dict:
    """Extract all relevant data from a problem file.
    
    Args:
        problem_file: Path to problem .tex file
        
    Returns:
        Dictionary with problem data:
        {
            'number': int,
            'chapter': str,
            'topic': str,
            'subtopic': str,
            'type': str,
            'ideas': dict,
            'content': str,
            'question': str,
            'solution': str
        }
    """
    if not problem_file.exists():
        return None
    
    content = problem_file.read_text(encoding='utf-8')
    
    # Extract problem number from filename (problem_5.tex -> 5)
    match = re.search(r'problem_(\d+)', problem_file.name)
    problem_num = int(match.group(1)) if match else None
    
    # Extract metadata from comments
    metadata = extract_metadata(content)
    
    # Try to load classification data if available
    classification_file = problem_file.parent.parent / 'classifications' / f'problem_{problem_num}.json'
    if classification_file.exists():
        import json
        try:
            with open(classification_file, 'r', encoding='utf-8') as f:
                classification = json.load(f)
                # Merge classification data with metadata (metadata takes precedence)
                for key in ['chapter', 'topic', 'subtopic', 'subject']:
                    if not metadata.get(key) and classification.get(key):
                        metadata[key] = classification[key]
        except Exception:
            pass  # Ignore errors reading classification
    
    # Extract different parts
    ideas = parse_idea_block(content)
    question = extract_question(content)
    solution = extract_solution(content)
    
    return {
        'number': problem_num,
        'chapter': metadata.get('chapter', 'Unknown'),
        'topic': metadata.get('topic', 'Unknown'),
        'subtopic': metadata.get('subtopic', ''),
        'type': metadata.get('type', 'mcq'),
        'subject': metadata.get('subject', 'physics'),
        'ideas': ideas,
        'content': content,
        'question': question,
        'solution': solution,
        'file': str(problem_file)
    }


def extract_metadata(content: str) -> dict:
    """Extract metadata from comment lines at the top of the file.
    
    Args:
        content: LaTeX file content
        
    Returns:
        Dictionary with metadata fields
    """
    metadata = {}
    
    # Extract from comment lines (% key: value)
    for line in content.split('\n')[:20]:  # Check first 20 lines
        line = line.strip()
        if line.startswith('%'):
            # Remove % and split by :
            line = line[1:].strip()
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
    
    return metadata


def extract_question(content: str) -> str:
    """Extract the question text (everything before \\begin{solution}).
    
    Args:
        content: LaTeX file content
        
    Returns:
        Question text
    """
    # Find content before solution block
    solution_match = re.search(r'\\begin\{solution\}', content)
    if solution_match:
        question = content[:solution_match.start()].strip()
    else:
        # No solution block, try to find before idea block
        idea_match = re.search(r'\\begin\{idea\}', content)
        if idea_match:
            question = content[:idea_match.start()].strip()
        else:
            question = content.strip()
    
    return question


def extract_solution(content: str) -> str:
    """Extract the solution block content.
    
    Args:
        content: LaTeX file content
        
    Returns:
        Solution text (without idea block)
    """
    # Find solution block
    solution_match = re.search(
        r'\\begin\{solution\}(.*?)\\end\{solution\}',
        content,
        re.DOTALL
    )
    
    if not solution_match:
        return ""
    
    return solution_match.group(1).strip()


def parse_idea_block(content: str) -> dict:
    """Parse the \\begin{idea}...\\end{idea} block.
    
    Extracts concepts, formulas, and techniques from the idea environment.
    
    Args:
        content: LaTeX file content
        
    Returns:
        Dictionary with:
        {
            'raw': str (full idea block),
            'concepts': list[str],
            'formulas': list[str],
            'techniques': list[str]
        }
    """
    # Find idea block
    idea_match = re.search(
        r'\\begin\{idea\}(.*?)\\end\{idea\}',
        content,
        re.DOTALL
    )
    
    if not idea_match:
        return {'raw': '', 'concepts': [], 'formulas': [], 'techniques': []}
    
    idea_content = idea_match.group(1).strip()
    
    # Extract concepts (lines with \textbf{Concept:})
    concepts = []
    concept_matches = re.finditer(
        r'\\textbf\{Concept:\}(.*?)(?=\\textbf\{|\\intertext\{|\\end\{|$)',
        idea_content,
        re.DOTALL
    )
    for match in concept_matches:
        concept_text = match.group(1).strip()
        # Clean up LaTeX commands but keep the essence
        concept_text = re.sub(r'\\\\', '', concept_text)
        concept_text = re.sub(r'\s+', ' ', concept_text)
        if concept_text:
            concepts.append(concept_text)
    
    # Extract formulas (lines between align* or in math mode)
    formulas = []
    # Look for standalone equations or formulas
    formula_matches = re.finditer(
        r'(?:&=|=)\s*([^\\]+?)(?:\\\\|$)',
        idea_content
    )
    for match in formula_matches:
        formula = match.group(1).strip()
        if formula and len(formula) > 2:  # Skip very short matches
            formulas.append(formula)
    
    # Extract techniques (lines with \textbf{Technique:})
    techniques = []
    technique_matches = re.finditer(
        r'\\textbf\{Technique:\}(.*?)(?=\\textbf\{|\\intertext\{|\\end\{|$)',
        idea_content,
        re.DOTALL
    )
    for match in technique_matches:
        technique_text = match.group(1).strip()
        technique_text = re.sub(r'\\\\', '', technique_text)
        technique_text = re.sub(r'\s+', ' ', technique_text)
        if technique_text:
            techniques.append(technique_text)
    
    return {
        'raw': idea_content,
        'concepts': concepts,
        'formulas': formulas,
        'techniques': techniques
    }


def scan_problem_directory(directory: Path) -> list[dict]:
    """Scan a directory for all problem files and extract their data.
    
    Discovery logic:
    1. If directory directly contains problem_*.tex → use those.
    2. Otherwise, recursively search for **/problem_*.tex (handles
       year-wise layouts like 2024/agentic/scans/problem_1.tex).
    
    Args:
        directory: Path to directory (or parent) containing problem .tex files
        
    Returns:
        List of problem data dictionaries
    """
    problems = []
    
    # Try direct match first
    problem_files = sorted(directory.glob('problem_*.tex'))
    
    # If nothing found, auto-discover recursively
    if not problem_files:
        problem_files = sorted(directory.rglob('problem_*.tex'))
    
    for problem_file in problem_files:
        data = extract_problem_data(problem_file)
        if data and data['number']:
            problems.append(data)
    
    # Sort by problem number
    problems.sort(key=lambda x: x['number'])
    
    return problems
