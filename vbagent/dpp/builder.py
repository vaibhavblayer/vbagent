"""DPP Builder - Creates Daily Practice Problem sets from question banks.

This module provides smart selection strategies for creating balanced DPP sets
with proper difficulty distribution, topic coverage, and usage tracking.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from vbagent.metadata.store import MetadataStore, QuestionMetadata


class SelectionStrategy(ABC):
    """Abstract base class for question selection strategies."""
    
    @abstractmethod
    def select(
        self,
        available: list[QuestionMetadata],
        count: int
    ) -> list[QuestionMetadata]:
        """Select questions according to the strategy.
        
        Args:
            available: List of available questions to select from
            count: Number of questions to select
            
        Returns:
            List of selected QuestionMetadata objects
        """
        pass


class BalancedStrategy(SelectionStrategy):
    """Balance difficulty distribution in DPP.
    
    Aims for approximately:
    - 40% easy questions
    - 40% medium questions  
    - 20% hard questions
    
    Prefers less-used questions when multiple options are available.
    """
    
    def select(
        self,
        available: list[QuestionMetadata],
        count: int
    ) -> list[QuestionMetadata]:
        """Select questions with balanced difficulty distribution.
        
        Args:
            available: List of available questions
            count: Number of questions to select
            
        Returns:
            List of selected questions with balanced difficulty
        """
        if not available:
            return []
        
        if len(available) <= count:
            return available
        
        # Group by difficulty
        by_difficulty = {
            "easy": [],
            "medium": [],
            "hard": [],
            "unknown": []
        }
        
        for q in available:
            difficulty = q.difficulty or "unknown"
            if difficulty not in by_difficulty:
                difficulty = "unknown"
            by_difficulty[difficulty].append(q)
        
        # Sort each group by usage (prefer less-used questions)
        for difficulty in by_difficulty:
            by_difficulty[difficulty].sort(key=lambda q: (q.usage_count, q.last_used or datetime.min))
        
        # Calculate target counts (40% easy, 40% medium, 20% hard)
        target_easy = int(count * 0.4)
        target_medium = int(count * 0.4)
        target_hard = count - target_easy - target_medium  # Remaining goes to hard
        
        selected = []
        
        # Select easy questions
        easy_available = by_difficulty["easy"]
        easy_count = min(target_easy, len(easy_available))
        selected.extend(easy_available[:easy_count])
        
        # Select medium questions
        medium_available = by_difficulty["medium"]
        medium_count = min(target_medium, len(medium_available))
        selected.extend(medium_available[:medium_count])
        
        # Select hard questions
        hard_available = by_difficulty["hard"]
        hard_count = min(target_hard, len(hard_available))
        selected.extend(hard_available[:hard_count])
        
        # If we don't have enough questions, fill from unknown or other difficulties
        remaining_needed = count - len(selected)
        if remaining_needed > 0:
            # Collect remaining questions
            remaining = []
            remaining.extend(easy_available[easy_count:])
            remaining.extend(medium_available[medium_count:])
            remaining.extend(hard_available[hard_count:])
            remaining.extend(by_difficulty["unknown"])
            
            # Sort by usage and take what we need
            remaining.sort(key=lambda q: (q.usage_count, q.last_used or datetime.min))
            selected.extend(remaining[:remaining_needed])
        
        return selected[:count]


class TopicCoverageStrategy(SelectionStrategy):
    """Maximize topic diversity in DPP.
    
    Selects questions to cover as many different topics as possible,
    ensuring broad coverage of the question bank.
    """
    
    def select(
        self,
        available: list[QuestionMetadata],
        count: int
    ) -> list[QuestionMetadata]:
        """Select questions to maximize topic diversity.
        
        Args:
            available: List of available questions
            count: Number of questions to select
            
        Returns:
            List of selected questions with maximum topic coverage
        """
        if not available:
            return []
        
        if len(available) <= count:
            return available
        
        # Group by topic
        by_topic: dict[str, list[QuestionMetadata]] = {}
        no_topic: list[QuestionMetadata] = []
        
        for q in available:
            if q.topic:
                if q.topic not in by_topic:
                    by_topic[q.topic] = []
                by_topic[q.topic].append(q)
            else:
                no_topic.append(q)
        
        # Sort questions within each topic by usage
        for topic in by_topic:
            by_topic[topic].sort(key=lambda q: (q.usage_count, q.last_used or datetime.min))
        
        # Sort no_topic questions by usage
        no_topic.sort(key=lambda q: (q.usage_count, q.last_used or datetime.min))
        
        # Round-robin selection from topics
        selected = []
        topic_lists = list(by_topic.values())
        topic_index = 0
        
        while len(selected) < count and (topic_lists or no_topic):
            # Try to select from next topic
            if topic_lists:
                current_list = topic_lists[topic_index]
                if current_list:
                    selected.append(current_list.pop(0))
                    if len(selected) >= count:
                        break
                
                # Remove empty topic lists
                if not current_list:
                    topic_lists.pop(topic_index)
                    if topic_lists:
                        topic_index = topic_index % len(topic_lists)
                else:
                    topic_index = (topic_index + 1) % len(topic_lists)
            
            # If no more topics, fill from no_topic
            if not topic_lists and no_topic and len(selected) < count:
                selected.append(no_topic.pop(0))
        
        return selected[:count]


class RandomStrategy(SelectionStrategy):
    """Random selection strategy.
    
    Randomly selects questions from the available pool,
    with preference for less-used questions.
    """
    
    def select(
        self,
        available: list[QuestionMetadata],
        count: int
    ) -> list[QuestionMetadata]:
        """Randomly select questions, preferring less-used ones.
        
        Args:
            available: List of available questions
            count: Number of questions to select
            
        Returns:
            List of randomly selected questions
        """
        if not available:
            return []
        
        if len(available) <= count:
            return available
        
        # Sort by usage (prefer less-used)
        sorted_questions = sorted(
            available,
            key=lambda q: (q.usage_count, q.last_used or datetime.min)
        )
        
        # Take top 2*count least-used questions and randomly sample from them
        # This balances randomness with usage fairness
        pool_size = min(len(sorted_questions), count * 2)
        pool = sorted_questions[:pool_size]
        
        return random.sample(pool, min(count, len(pool)))


@dataclass
class DPPResult:
    """Result of DPP creation.
    
    Attributes:
        questions: List of selected questions
        main_tex_path: Path to generated main.tex file
        strategy_used: Name of the selection strategy used
        created_at: Timestamp of creation
    """
    questions: list[QuestionMetadata]
    main_tex_path: Path
    strategy_used: str
    created_at: datetime = field(default_factory=datetime.now)
    
    def compile(self, output_dir: Optional[Path] = None, verbose: bool = False) -> tuple[bool, str]:
        """Compile DPP to PDF.
        
        Args:
            output_dir: Directory to save PDF (defaults to same as main.tex)
            verbose: Whether to show verbose compilation output
            
        Returns:
            Tuple of (success, pdf_path or error_message)
        """
        import shutil
        import subprocess
        
        if not self.main_tex_path.exists():
            return False, f"main.tex not found: {self.main_tex_path}"
        
        # Check pdflatex is available
        if not shutil.which("pdflatex"):
            return False, "pdflatex not found. Install TeX Live or MacTeX."
        
        # Determine output directory
        if output_dir is None:
            output_dir = self.main_tex_path.parent
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run pdflatex directly on the complete document
        # The DPP already has a complete LaTeX document, so we don't need compile_latex()
        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory", str(output_dir),
            str(self.main_tex_path),
        ]
        
        try:
            if verbose:
                # Stream output to terminal
                import sys
                print(f"\n$ {' '.join(cmd)}\n", flush=True)
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.main_tex_path.parent),
                )
                stdout_lines = []
                while True:
                    line = proc.stdout.readline()
                    if not line and proc.poll() is not None:
                        break
                    if line:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                        stdout_lines.append(line)
                proc.wait(timeout=30)
                returncode = proc.returncode
            else:
                # Silent mode
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(self.main_tex_path.parent),
                )
                returncode = result.returncode
                stdout_lines = result.stdout.splitlines()
            
            # Check for PDF output
            pdf_name = self.main_tex_path.stem + ".pdf"
            pdf_path = output_dir / pdf_name
            
            if returncode == 0 and pdf_path.exists():
                return True, str(pdf_path)
            else:
                # Parse errors from output
                error_lines = [line for line in stdout_lines if line.startswith("!") or "Error" in line]
                error_msg = "\n".join(error_lines[:5]) if error_lines else "Compilation failed (check log)"
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            return False, "pdflatex timed out (possible infinite loop)"
        except Exception as e:
            return False, f"Compilation error: {e}"


class DPPBuilder:
    """Builds DPP sets from question banks.
    
    Provides multiple selection strategies for creating balanced,
    diverse, or random DPP sets.
    """
    
    def __init__(self, metadata_store: MetadataStore):
        """Initialize DPP builder.
        
        Args:
            metadata_store: MetadataStore instance for querying questions
        """
        self.metadata_store = metadata_store
        self.strategies: dict[str, SelectionStrategy] = {
            "balanced": BalancedStrategy(),
            "topic_coverage": TopicCoverageStrategy(),
            "random": RandomStrategy(),
        }
    
    def create_dpp(
        self,
        count: int,
        strategy: str = "balanced",
        filters: Optional[dict] = None,
        output_path: Optional[Path] = None,
        title: str = "Daily Practice Problem Set"
    ) -> DPPResult:
        """Create a DPP set.
        
        Args:
            count: Number of questions to include
            strategy: Selection strategy ("balanced", "topic_coverage", "random")
            filters: Optional filters for question selection (topic, difficulty, chapter, etc.)
            output_path: Path for main.tex file (defaults to ./dpp_TIMESTAMP.tex)
            title: Title for the DPP document
            
        Returns:
            DPPResult with selected questions and generated files
            
        Raises:
            ValueError: If strategy is unknown or insufficient questions available
        """
        if strategy not in self.strategies:
            raise ValueError(
                f"Unknown strategy: {strategy}. "
                f"Available: {', '.join(self.strategies.keys())}"
            )
        
        # Query available questions with filters
        filters = filters or {}
        available = self.metadata_store.query(
            topic=filters.get("topic"),
            difficulty=filters.get("difficulty"),
            chapter=filters.get("chapter"),
            question_type=filters.get("question_type"),
            tags=filters.get("tags"),
        )
        
        if not available:
            raise ValueError("No questions found matching the specified filters")
        
        if len(available) < count:
            raise ValueError(
                f"Insufficient questions: requested {count}, "
                f"but only {len(available)} available"
            )
        
        # Select questions using strategy
        strategy_obj = self.strategies[strategy]
        selected = strategy_obj.select(available, count)
        
        # Generate output path if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"dpp_{timestamp}.tex")
        
        # Ensure output path has .tex extension
        if output_path.suffix != ".tex":
            output_path = output_path.with_suffix(".tex")
        
        # Generate main.tex
        self._generate_main_tex(selected, output_path, title)
        
        # Update usage statistics for selected questions
        for question in selected:
            self.metadata_store.update_usage(question.file_path)
        
        return DPPResult(
            questions=selected,
            main_tex_path=output_path,
            strategy_used=strategy
        )
    
    def _generate_main_tex(
        self,
        questions: list[QuestionMetadata],
        output_path: Path,
        title: str
    ) -> None:
        """Generate main.tex file for DPP.
        
        Args:
            questions: List of selected questions
            output_path: Path to write main.tex
            title: Document title
        """
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build LaTeX document
        lines = [
            r"\documentclass[12pt,a4paper]{article}",
            r"",
            r"% Packages",
            r"\usepackage{amsmath, amssymb, amsthm, mathtools}",
            r"\usepackage{tikz}",
            r"\usepackage{pgfplots}",
            r"\usepackage[american]{circuitikz}",
            r"\usepackage{tasks}",
            r"\usepackage{enumitem}",
            r"\usepackage{geometry}",
            r"\usepackage{xcolor}",
            r"\usepackage{comment}",
            r"\usepackage{siunitx}",
            r"\usepackage{upgreek}",
            r"\usepackage[utopia]{mathdesign}",
            r"\geometry{margin=1in}",
            r"",
            r"% TikZ libraries",
            r"\usetikzlibrary{calc, decorations.pathmorphing, decorations.markings,",
            r"                patterns, arrows.meta, positioning, shapes.geometric,",
            r"                intersections, angles, quotes}",
            r"",
            r"% Custom commands and environments",
            r"\newcommand{\ans}{\quad}",
            r"\newcommand{\ansint}[1]{\textcolor{red!95}{#1}}",
            r"\newenvironment{solution}{\par\color{red!85!black}$\Rightarrow$}{}",
            r"\newenvironment{alternatesolution}{\par\color{blue!90!black}$\Rightarrow$}{}",
            r"\newenvironment{idea}{\par\color{purple!90!black}$\Rightarrow$}{}",
            r"% \excludecomment{solution}  % Uncomment to hide solutions",
            r"% \excludecomment{alternatesolution}  % Uncomment to hide alternate solutions",
            r"% \excludecomment{idea}  % Uncomment to hide ideas",
            r"",
            r"% Document info",
            f"\\title{{{title}}}",
            r"\date{\today}",
            r"",
            r"\begin{document}",
            r"\maketitle",
            r"",
            r"\begin{enumerate}",
            r"",
        ]
        
        # Add each question
        for i, question in enumerate(questions, 1):
            # Add question metadata as comment
            lines.append(f"% Question {i}")
            lines.append(f"% File: {question.file_path}")
            if question.topic:
                lines.append(f"% Topic: {question.topic}")
            if question.difficulty:
                lines.append(f"% Difficulty: {question.difficulty}")
            lines.append("")
            
            # Read question content
            try:
                question_path = Path(question.file_path)
                if question_path.exists():
                    content = question_path.read_text(encoding="utf-8")
                    # Add the question content
                    lines.append(content.strip())
                else:
                    lines.append(f"\\item [Question file not found: {question.file_path}]")
            except Exception as e:
                lines.append(f"\\item [Error reading question: {e}]")
            
            lines.append("")
        
        # Close document
        lines.extend([
            r"\end{enumerate}",
            r"\end{document}",
        ])
        
        # Write to file
        output_path.write_text("\n".join(lines), encoding="utf-8")
