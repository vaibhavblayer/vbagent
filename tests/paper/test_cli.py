"""Tests for paper CLI commands — click invocation tests."""

from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest
from click.testing import CliRunner

from vbagent.cli.paper.paper_commands import paper


@pytest.fixture
def runner():
    return CliRunner()


class TestPaperCLI:
    def test_paper_help(self, runner):
        result = runner.invoke(paper, ["--help"])
        assert result.exit_code == 0
        assert "Paper generation" in result.output

    def test_paper_init_help(self, runner):
        result = runner.invoke(paper, ["init", "--help"])
        assert result.exit_code == 0
        assert "--subject" in result.output
        assert "--tone" in result.output

    def test_paper_generate_help(self, runner):
        result = runner.invoke(paper, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--topic" in result.output
        assert "--tone" in result.output
        assert "--no-solution" in result.output

    def test_paper_solve_help(self, runner):
        result = runner.invoke(paper, ["solve", "--help"])
        assert result.exit_code == 0
        assert "--problems" in result.output

    def test_paper_hint_help(self, runner):
        result = runner.invoke(paper, ["hint", "--help"])
        assert result.exit_code == 0
        assert "--style" in result.output
        assert "conceptual" in result.output

    def test_paper_status_help(self, runner):
        result = runner.invoke(paper, ["status", "--help"])
        assert result.exit_code == 0

    def test_paper_qa_help(self, runner):
        result = runner.invoke(paper, ["qa", "--help"])
        assert result.exit_code == 0

    def test_paper_tones_help(self, runner):
        result = runner.invoke(paper, ["tones", "--help"])
        assert result.exit_code == 0
        assert "--subject" in result.output


class TestTonesCommand:
    def test_tones_lists_all_subjects(self, runner):
        result = runner.invoke(paper, ["tones"])
        assert result.exit_code == 0
        assert "Physics" in result.output
        assert "Chemistry" in result.output
        assert "Mathematics" in result.output
        assert "symmetry-heavy" in result.output
        assert "mechanistic" in result.output
        assert "competition-style" in result.output

    def test_tones_filter_by_subject(self, runner):
        result = runner.invoke(paper, ["tones", "--subject", "physics"])
        assert result.exit_code == 0
        assert "Physics" in result.output
        assert "symmetry-heavy" in result.output
        assert "mechanistic" not in result.output
        assert "competition-style" not in result.output

    def test_tones_chemistry_only(self, runner):
        result = runner.invoke(paper, ["tones", "--subject", "chemistry"])
        assert result.exit_code == 0
        assert "Chemistry" in result.output
        assert "mechanistic" in result.output
        assert "symmetry-heavy" not in result.output


class TestInitCommand:
    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_init_basic(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch.init_paper.return_value = MagicMock(
            problems=[], subject="physics", tone="",
        )
        mock_orch.manifest = MagicMock()
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, ["init", "--subject", "physics", "--paper-dir", str(tmp_path)])
        assert result.exit_code == 0

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_init_with_tone(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        state = MagicMock(problems=[], subject="physics", tone="")
        mock_orch = MagicMock()
        mock_orch.init_paper.return_value = state
        mock_orch.manifest = MagicMock()
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, [
            "init", "--subject", "physics", "--tone", "symmetry-heavy",
            "--paper-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert state.tone == "symmetry-heavy"


class TestGenerateCommand:
    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_generate_standalone(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, [
            "generate", "--topic", "electrostatics", "--type", "mcq_sc",
            "--paper-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        mock_orch.generate_standalone.assert_called_once()
        call_kwargs = mock_orch.generate_standalone.call_args[1]
        assert call_kwargs["topic"] == "electrostatics"
        assert call_kwargs["question_type"] == "mcq_sc"

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_generate_with_tone(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, [
            "generate", "--topic", "mechanics", "--tone", "energy-methods",
            "--paper-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        call_kwargs = mock_orch.generate_standalone.call_args[1]
        assert call_kwargs["tone"] == "energy-methods"

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_generate_no_solution(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, [
            "generate", "--topic", "optics", "--no-solution",
            "--paper-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        call_kwargs = mock_orch.generate_standalone.call_args[1]
        assert call_kwargs["with_solution"] is False

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_generate_syllabus_driven(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch.generate_problems.return_value = MagicMock(
            total_generated=3, total_requested=5, coverage_before=50.0, coverage_after=80.0,
        )
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, [
            "generate", "--count", "5", "--paper-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        mock_orch.generate_problems.assert_called_once()


class TestEnrichCommand:
    def test_enrich_help(self, runner):
        result = runner.invoke(paper, ["enrich", "--help"])
        assert result.exit_code == 0
        assert "--problems" in result.output

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_enrich_basic(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch.enrich_problems.return_value = [
            {"serial": 1, "subtopic": "Lagrangian mechanics", "concepts": ["Lagrangian"], "success": True},
        ]
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, ["enrich", "--paper-dir", str(tmp_path)])
        assert result.exit_code == 0
        mock_orch.enrich_problems.assert_called_once_with(problem_ids=None)

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_enrich_specific_problems(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch.enrich_problems.return_value = []
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, ["enrich", "--problems", "1,3", "--paper-dir", str(tmp_path)])
        assert result.exit_code == 0
        mock_orch.enrich_problems.assert_called_once_with(problem_ids=[1, 3])
