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
        assert "--exam" in result.output
        assert "--chapter" in result.output
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
    @staticmethod
    def _report():
        return MagicMock(
            total_generated=1,
            total_requested=1,
            accepted=1,
            needs_review=0,
            rejected=0,
            failed=0,
            authoring_run_id="run-1",
            authoring_run_dir="/tmp/run-1",
        )

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_generate_routes_to_canonical_authoring(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch.author_problems.return_value = self._report()
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, [
            "generate",
            "--exam", "jee_main",
            "--subject", "physics",
            "--chapter", "electrostatics",
            "--topic", "electric_field",
            "--type", "mcq_sc",
            "--paper-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        mock_orch.author_problems.assert_called_once()
        request = mock_orch.author_problems.call_args.args[0]
        assert request.exam == "jee_main"
        assert request.subject == "physics"
        assert request.chapter == "electrostatics"
        assert request.topics == ["electric_field"]
        assert request.question_types == {"mcq_sc": 1.0}

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_generate_with_tone(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch.author_problems.return_value = self._report()
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, [
            "generate",
            "--exam", "jee_main",
            "--subject", "physics",
            "--chapter", "kinematics",
            "--tone", "energy-methods",
            "--paper-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        request = mock_orch.author_problems.call_args.args[0]
        assert request.tone == "energy-methods"
        assert request.question_types == {"mcq_sc": 1.0}

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_generate_no_solution_is_rejected(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, [
            "generate",
            "--exam", "jee_main",
            "--subject", "physics",
            "--chapter", "optics",
            "--no-solution",
            "--paper-dir", str(tmp_path),
        ])
        assert result.exit_code == 2
        assert "independent solution is a required acceptance gate" in result.output
        mock_orch.author_problems.assert_not_called()

    @patch("vbagent.paper.orchestrator.PaperOrchestrator")
    @patch("vbagent.cli.common._get_console")
    def test_generate_entire_chapter(self, mock_console, mock_orch_cls, runner, tmp_path):
        mock_console.return_value = MagicMock()
        mock_orch = MagicMock()
        report = self._report()
        report.total_generated = 3
        report.total_requested = 5
        mock_orch.author_problems.return_value = report
        mock_orch_cls.return_value = mock_orch

        result = runner.invoke(paper, [
            "generate",
            "--exam", "jee_main",
            "--subject", "physics",
            "--chapter", "kinematics",
            "--count", "5",
            "--paper-dir", str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "did not import every requested" in result.output
        request = mock_orch.author_problems.call_args.args[0]
        assert request.count == 5
        assert request.topics == []

    def test_generate_requires_exact_identity(self, runner):
        result = runner.invoke(paper, ["generate", "--subject", "physics"])
        assert result.exit_code == 2
        assert "--exam" in result.output


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
