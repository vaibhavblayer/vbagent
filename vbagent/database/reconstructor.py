"""Reconstruct LaTeX files from database records."""

from .store import QuestionRecord


def reconstruct_tex_file(parent: QuestionRecord, children: list[QuestionRecord] = None) -> str:
    """Reconstruct full .tex file from database record(s).
    
    Args:
        parent: Main question record (or passage parent)
        children: List of child questions (for passage type)
    
    Returns:
        Complete LaTeX content
    """
    if parent.is_passage and children:
        return _reconstruct_passage(parent, children)
    else:
        return _reconstruct_standalone(parent)


def _reconstruct_passage(parent: QuestionRecord, children: list[QuestionRecord]) -> str:
    """Reconstruct passage with sub-questions."""
    tex = ""
    
    # Add metadata comments
    tex += _generate_metadata_comments(parent)
    
    # Add passage text
    if parent.passage_text:
        tex += f"{parent.passage_text}\n\n"
    
    # Add each sub-question
    for i, child in enumerate(children, 1):
        tex += f"\\item {child.problem_latex}\n\n"
        
        # Add problem TikZ
        for tikz in child.tikz_diagrams:
            if tikz['context'] == 'problem':
                tex += f"{tikz['code']}\n\n"
        
        # Add solution
        if child.solution_latex:
            tex += "\\begin{solution}\n"
            tex += f"{child.solution_latex}\n\n"
            
            # Add solution TikZ
            for tikz in child.tikz_diagrams:
                if tikz['context'] == 'solution':
                    tex += f"{tikz['code']}\n\n"
            
            tex += "\\end{solution}\n\n"
        
        # Add alternate solution
        if child.alternate_solution_latex:
            tex += "\\begin{alternatesolution}\n"
            tex += f"{child.alternate_solution_latex}\n\n"
            
            # Add alternate TikZ
            for tikz in child.tikz_diagrams:
                if tikz['context'] == 'alternate':
                    tex += f"{tikz['code']}\n\n"
            
            tex += "\\end{alternatesolution}\n\n"
        
        # Add idea
        if child.idea_latex:
            tex += "\\begin{idea}\n"
            tex += f"{child.idea_latex}\n\n"
            
            # Add idea TikZ
            for tikz in child.tikz_diagrams:
                if tikz['context'] == 'idea':
                    tex += f"{tikz['code']}\n\n"
            
            tex += "\\end{idea}\n\n"
    
    return tex


def _reconstruct_standalone(record: QuestionRecord) -> str:
    """Reconstruct standalone question."""
    tex = ""
    
    # Add metadata comments
    tex += _generate_metadata_comments(record)
    
    # Add problem
    tex += f"\\item {record.problem_latex}\n\n"
    
    # Add problem TikZ
    for tikz in record.tikz_diagrams:
        if tikz['context'] == 'problem':
            tex += f"{tikz['code']}\n\n"
    
    # Add solution
    if record.solution_latex:
        tex += "\\begin{solution}\n"
        tex += f"{record.solution_latex}\n\n"
        
        # Add solution TikZ
        for tikz in record.tikz_diagrams:
            if tikz['context'] == 'solution':
                tex += f"{tikz['code']}\n\n"
        
        tex += "\\end{solution}\n\n"
    
    # Add alternate solution
    if record.alternate_solution_latex:
        tex += "\\begin{alternatesolution}\n"
        tex += f"{record.alternate_solution_latex}\n\n"
        
        # Add alternate TikZ
        for tikz in record.tikz_diagrams:
            if tikz['context'] == 'alternate':
                tex += f"{tikz['code']}\n\n"
        
        tex += "\\end{alternatesolution}\n\n"
    
    # Add idea
    if record.idea_latex:
        tex += "\\begin{idea}\n"
        tex += f"{record.idea_latex}\n\n"
        
        # Add idea TikZ
        for tikz in record.tikz_diagrams:
            if tikz['context'] == 'idea':
                tex += f"{tikz['code']}\n\n"
        
        tex += "\\end{idea}\n\n"
    
    return tex


def _generate_metadata_comments(record: QuestionRecord) -> str:
    """Generate metadata comment block."""
    comments = []
    
    if record.subject:
        comments.append(f"% subject: {record.subject}")
    if record.chapter:
        comments.append(f"% chapter: {record.chapter}")
    if record.topic:
        comments.append(f"% topic: {record.topic}")
    if record.subtopic:
        comments.append(f"% subtopic: {record.subtopic}")
    if record.difficulty:
        comments.append(f"% difficulty: {record.difficulty}")
    if record.question_type:
        comments.append(f"% type: {record.question_type}")
    if record.tags:
        comments.append(f"% tags: {', '.join(record.tags)}")
    if record.key_concepts:
        comments.append(f"% key_concepts: {', '.join(record.key_concepts)}")
    if record.requires_calculus:
        comments.append(f"% requires_calculus: true")
    
    if comments:
        return "\n".join(comments) + "\n\n"
    return ""
