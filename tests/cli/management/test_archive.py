"""Unit tests for archive command MCQ option extraction."""

import pytest
from pathlib import Path
import tempfile
import shutil

from vbagent.cli.management.archive import (
    _parse_tex,
    _extract_mcq_correct_option,
)


class TestMCQOptionExtraction:
    """Test MCQ option parsing and extraction."""

    def test_parse_tex_removes_ans_from_question(self):
        """Test that _parse_tex removes \\ans markers from question.svg."""
        content = r"""
\item A particle moves with velocity $v = 5$ m/s.

\begin{tasks}(2)
\task $10$ m/s
\task $15$ m/s \ans
\task $20$ m/s
\task $25$ m/s
\end{tasks}

\begin{solution}
The answer is B.
\end{solution}
"""
        parts = _parse_tex(content)
        
        # Check that question exists and has no \ans marker
        assert "question" in parts
        assert r"\ans" not in parts["question"]
        
        # Check that question still has all options
        assert r"\begin{tasks}" in parts["question"]
        assert "$15$ m/s" in parts["question"]
        
        # Check that combined still has \ans marker
        assert "combined" in parts
        assert r"\ans" in parts["combined"]

    def test_extract_mcq_correct_option_single(self):
        """Test extracting single correct MCQ option."""
        content = r"""
\item Question text

\begin{tasks}(2)
\task Option A
\task Option B \ans
\task Option C
\task Option D
\end{tasks}
"""
        result = _extract_mcq_correct_option(content)
        assert result == "B"

    def test_extract_mcq_correct_option_multiple(self):
        """Test extracting multiple correct MCQ options."""
        content = r"""
\item Question text

\begin{tasks}(2)
\task Option A \ans
\task Option B
\task Option C \ans
\task Option D
\end{tasks}
"""
        result = _extract_mcq_correct_option(content)
        assert result == "A,C"

    def test_extract_mcq_correct_option_first(self):
        """Test extracting when first option is correct."""
        content = r"""
\item Question text

\begin{tasks}(2)
\task Option A \ans
\task Option B
\task Option C
\task Option D
\end{tasks}
"""
        result = _extract_mcq_correct_option(content)
        assert result == "A"

    def test_extract_mcq_correct_option_last(self):
        """Test extracting when last option is correct."""
        content = r"""
\item Question text

\begin{tasks}(2)
\task Option A
\task Option B
\task Option C
\task Option D \ans
\end{tasks}
"""
        result = _extract_mcq_correct_option(content)
        assert result == "D"

    def test_extract_mcq_no_tasks_environment(self):
        """Test that non-MCQ returns None."""
        content = r"""
\item This is a subjective question.

\begin{solution}
The answer is 42.
\end{solution}
"""
        result = _extract_mcq_correct_option(content)
        assert result is None

    def test_extract_mcq_no_answer_marker(self):
        """Test that MCQ without \ans marker returns None."""
        content = r"""
\item Question text

\begin{tasks}(2)
\task Option A
\task Option B
\task Option C
\task Option D
\end{tasks}
"""
        result = _extract_mcq_correct_option(content)
        assert result is None

    def test_parse_tex_with_diagram_in_question(self):
        """Test that diagrams in question are preserved."""
        content = r"""
\item Question with diagram

\begin{center}
\begin{tikzpicture}
\draw (0,0) -- (1,1);
\end{tikzpicture}
\end{center}

\begin{tasks}(2)
\task A
\task B \ans
\task C
\task D
\end{tasks}

\begin{solution}
Solution text
\end{solution}
"""
        parts = _parse_tex(content)
        
        # Question should have the diagram
        assert "question" in parts
        assert r"\begin{tikzpicture}" in parts["question"]
        
        # But no \ans marker
        assert r"\ans" not in parts["question"]
