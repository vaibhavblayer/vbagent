"""Tests for QAPipeline — checker chaining with mocked agents."""

from unittest.mock import MagicMock, patch
import pytest

from vbagent.paper.qa import QAPipeline
from vbagent.paper.models import QAResult


class TestQAPipeline:
    def setup_method(self):
        self.qa = QAPipeline(config=MagicMock(), console=MagicMock())

    @patch("vbagent.agents.quality.grammar_checker.check_grammar")
    @patch("vbagent.agents.quality.clarity_checker.check_clarity")
    @patch("vbagent.agents.quality.format_checker.check_format")
    def test_all_pass(self, mock_fmt, mock_clar, mock_gram):
        for m in (mock_fmt, mock_clar, mock_gram):
            m.return_value = MagicMock(passed=True, issues=[])

        result = self.qa.run("\\item Q", "\\begin{solution}A\\end{solution}")
        assert isinstance(result, QAResult)
        assert result.passed is True
        assert len(result.checks) == 3
        assert all(c.passed for c in result.checks)
        assert result.fixed_tex is None

    @patch("vbagent.agents.quality.latex_fixer.fix_latex")
    @patch("vbagent.agents.quality.grammar_checker.check_grammar")
    @patch("vbagent.agents.quality.clarity_checker.check_clarity")
    @patch("vbagent.agents.quality.format_checker.check_format")
    def test_format_fails_triggers_autofix(self, mock_fmt, mock_clar, mock_gram, mock_fix):
        mock_fmt.return_value = MagicMock(passed=False, issues=["missing \\item"])
        mock_clar.return_value = MagicMock(passed=True, issues=[])
        mock_gram.return_value = MagicMock(passed=True, issues=[])
        mock_fix.return_value = "\\item Fixed Q"

        result = self.qa.run("Q without item")
        assert result.passed is False
        assert result.fixed_tex == "\\item Fixed Q"
        # The failed check should be marked auto_fixed
        fmt_check = next(c for c in result.checks if c.checker == "format")
        assert fmt_check.auto_fixed is True

    @patch("vbagent.agents.quality.grammar_checker.check_grammar")
    @patch("vbagent.agents.quality.clarity_checker.check_clarity")
    @patch("vbagent.agents.quality.format_checker.check_format")
    def test_checker_exception_treated_as_failure(self, mock_fmt, mock_clar, mock_gram):
        mock_fmt.side_effect = Exception("Agent unavailable")
        mock_clar.return_value = MagicMock(passed=True, issues=[])
        mock_gram.return_value = MagicMock(passed=True, issues=[])

        result = self.qa.run("\\item Q")
        assert result.passed is False
        fmt_check = next(c for c in result.checks if c.checker == "format")
        assert not fmt_check.passed
        assert "Agent unavailable" in fmt_check.issues[0]

    @patch("vbagent.agents.quality.grammar_checker.check_grammar")
    @patch("vbagent.agents.quality.clarity_checker.check_clarity")
    @patch("vbagent.agents.quality.format_checker.check_format")
    def test_solution_tex_optional(self, mock_fmt, mock_clar, mock_gram):
        for m in (mock_fmt, mock_clar, mock_gram):
            m.return_value = MagicMock(passed=True, issues=[])

        result = self.qa.run("\\item Q")
        assert result.passed is True

    @patch("vbagent.agents.quality.latex_fixer.fix_latex")
    @patch("vbagent.agents.quality.grammar_checker.check_grammar")
    @patch("vbagent.agents.quality.clarity_checker.check_clarity")
    @patch("vbagent.agents.quality.format_checker.check_format")
    def test_autofix_failure_returns_none(self, mock_fmt, mock_clar, mock_gram, mock_fix):
        mock_fmt.return_value = MagicMock(passed=False, issues=["bad"])
        mock_clar.return_value = MagicMock(passed=True, issues=[])
        mock_gram.return_value = MagicMock(passed=True, issues=[])
        mock_fix.side_effect = Exception("fixer broken")

        result = self.qa.run("bad tex")
        assert result.passed is False
        assert result.fixed_tex is None
