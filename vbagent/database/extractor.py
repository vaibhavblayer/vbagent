"""Extract content from LaTeX files."""

import re
from pathlib import Path
from typing import Optional

from .store import QuestionRecord


class ContentExtractor:
    """Extract content sections from LaTeX files."""
    
    @staticmethod
    def extract_from_file(tex_file: Path) -> list[QuestionRecord]:
        """Extract all questions from a .tex file.
        
        Returns list because a file might contain:
        - Single standalone question
        - Multiple standalone questions
        - Passage with sub-questions
        """
        content = tex_file.read_text(encoding='utf-8')
        
        # Check if it's a passage type
        if ContentExtractor._is_passage(content):
            return ContentExtractor._extract_passage(content, tex_file)
        else:
            return ContentExtractor._extract_standalone(content, tex_file)
    
    @staticmethod
    def _is_passage(content: str) -> bool:
        """Check if content is a passage/comprehension type."""
        # Look for passage indicators
        patterns = [
            r'\\textbf\{Passage',
            r'\\textbf\{Comprehension',
            r'\\textbf\{Paragraph',
            r'% type:\s*passage',
            r'% type:\s*comprehension',
        ]
        return any(re.search(p, content, re.IGNORECASE) for p in patterns)
    
    @staticmethod
    def _extract_passage(content: str, tex_file: Path) -> list[QuestionRecord]:
        """Extract passage and its sub-questions."""
        records = []
        
        # Extract passage text (before first \item)
        passage_match = re.search(r'(.*?)\\item', content, re.DOTALL)
        passage_text = passage_match.group(1).strip() if passage_match else ""
        
        # Remove metadata comments from passage text
        passage_text = re.sub(r'%.*?\n', '', passage_text)
        
        # Extract all \item blocks (sub-questions)
        item_pattern = r'\\item\s+(.*?)(?=\\item|$)'
        items = re.findall(item_pattern, content, re.DOTALL)
        
        if not items:
            return []
        
        # Extract file-level metadata
        file_metadata = ContentExtractor._extract_metadata(content)
        
        # Create parent passage record
        parent = QuestionRecord(
            file_path=str(tex_file),
            question_type='passage',
            is_passage=True,
            passage_text=passage_text,
            num_subquestions=len(items),
        )
        
        # Apply file-level metadata to parent
        for key, value in file_metadata.items():
            if value is not None and key != 'question_type':  # Don't override question_type
                setattr(parent, key, value)
        
        records.append(parent)
        
        # Create child records for each sub-question
        for i, item_content in enumerate(items, 1):
            child = ContentExtractor._extract_question_content(item_content)
            child.file_path = str(tex_file)
            child.passage_order = i
            # Inherit metadata from parent
            child.subject = parent.subject
            child.chapter = parent.chapter
            child.topic = parent.topic
            child.subtopic = parent.subtopic
            child.difficulty = parent.difficulty
            records.append(child)
        
        return records
    
    @staticmethod
    def _extract_standalone(content: str, tex_file: Path) -> list[QuestionRecord]:
        """Extract standalone question(s)."""
        records = []
        
        # Extract all \item blocks
        item_pattern = r'\\item\s+(.*?)(?=\\item|$)'
        items = re.findall(item_pattern, content, re.DOTALL)
        
        if not items:
            return []
        
        # Extract file-level metadata
        file_metadata = ContentExtractor._extract_metadata(content)
        
        for item_content in items:
            record = ContentExtractor._extract_question_content(item_content)
            record.file_path = str(tex_file)
            # Apply file-level metadata
            for key, value in file_metadata.items():
                if value is not None:
                    setattr(record, key, value)
            records.append(record)
        
        return records
    
    @staticmethod
    def _extract_question_content(item_content: str) -> QuestionRecord:
        """Extract content from a single question item."""
        record = QuestionRecord()
        
        # Extract problem (before solution/alternate/idea)
        problem_match = re.search(
            r'^(.*?)(?=\\begin\{solution\}|\\begin\{alternatesolution\}|\\begin\{idea\}|$)',
            item_content, re.DOTALL
        )
        if problem_match:
            record.problem_latex = problem_match.group(1).strip()
        
        # Detect question type from problem
        record.question_type = ContentExtractor._detect_question_type(record.problem_latex or "")
        
        # Extract solution
        solution_match = re.search(
            r'\\begin\{solution\}(.*?)\\end\{solution\}',
            item_content, re.DOTALL
        )
        if solution_match:
            record.solution_latex = solution_match.group(1).strip()
            record.has_solution = True
        
        # Extract alternate solution
        alt_match = re.search(
            r'\\begin\{alternatesolution\}(.*?)\\end\{alternatesolution\}',
            item_content, re.DOTALL
        )
        if alt_match:
            record.alternate_solution_latex = alt_match.group(1).strip()
            record.has_alternate = True
        
        # Extract idea
        idea_match = re.search(
            r'\\begin\{idea\}(.*?)\\end\{idea\}',
            item_content, re.DOTALL
        )
        if idea_match:
            record.idea_latex = idea_match.group(1).strip()
            record.has_idea = True
        
        # Extract TikZ diagrams with context
        record.tikz_diagrams = ContentExtractor._extract_tikz_with_context(item_content)
        record.has_tikz = len(record.tikz_diagrams) > 0
        record.tikz_count = len(record.tikz_diagrams)
        
        return record
    
    @staticmethod
    def _extract_tikz_with_context(content: str) -> list[dict]:
        """Extract TikZ diagrams with their context."""
        tikz_diagrams = []
        
        # Define sections
        sections = {
            'problem': r'^(.*?)(?=\\begin\{solution\}|\\begin\{alternatesolution\}|\\begin\{idea\}|$)',
            'solution': r'\\begin\{solution\}(.*?)\\end\{solution\}',
            'alternate': r'\\begin\{alternatesolution\}(.*?)\\end\{alternatesolution\}',
            'idea': r'\\begin\{idea\}(.*?)\\end\{idea\}',
        }
        
        for context, pattern in sections.items():
            section_match = re.search(pattern, content, re.DOTALL)
            if not section_match:
                continue
            
            section_content = section_match.group(1)
            
            # Find all TikZ environments
            tikz_patterns = [
                r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',
                r'\\begin\{circuitikz\}.*?\\end\{circuitikz\}',
            ]
            
            for tikz_pattern in tikz_patterns:
                matches = re.finditer(tikz_pattern, section_content, re.DOTALL)
                for i, match in enumerate(matches, 1):
                    tikz_diagrams.append({
                        'context': context,
                        'code': match.group(0),
                        'order': i,
                    })
        
        return tikz_diagrams
    
    @staticmethod
    def _extract_metadata(content: str) -> dict:
        """Extract metadata from comments."""
        metadata = {}
        
        patterns = {
            'subject': r'%\s*subject:\s*(.+)',
            'chapter': r'%\s*chapter:\s*(.+)',
            'topic': r'%\s*topic:\s*(.+)',
            'subtopic': r'%\s*subtopic:\s*(.+)',
            'difficulty': r'%\s*difficulty:\s*(easy|medium|hard)',
            'question_type': r'%\s*type:\s*(.+)',
            'tags': r'%\s*tags:\s*(.+)',
            'key_concepts': r'%\s*key_concepts:\s*(.+)',
            'requires_calculus': r'%\s*requires_calculus:\s*(true|false|yes|no)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                
                if key in ['tags', 'key_concepts']:
                    metadata[key] = [t.strip() for t in value.split(',')]
                elif key == 'requires_calculus':
                    metadata[key] = value.lower() in ['true', 'yes']
                else:
                    metadata[key] = value
        
        return metadata
    
    @staticmethod
    def _detect_question_type(problem_text: str) -> Optional[str]:
        """Detect question type from problem text."""
        if r'\begin{tasks}' in problem_text:
            # Check if multiple correct
            if r'\ans' in problem_text and problem_text.count(r'\ans') > 1:
                return 'mcq_mc'
            return 'mcq_sc'
        elif r'\ansint{' in problem_text:
            return 'integer'
        elif 'assertion' in problem_text.lower() and 'reason' in problem_text.lower():
            return 'assertion_reason'
        elif 'match' in problem_text.lower() and 'following' in problem_text.lower():
            return 'match'
        else:
            return 'subjective'
