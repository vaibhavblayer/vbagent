"""Tests for ProblemGenerator — strategy dispatch with mocked agents."""

from unittest.mock import MagicMock, patch
import pytest

from vbagent.paper.generator import ProblemGenerator
from vbagent.paper.models import GeneratedProblemResult, GenerationTarget


class TestProblemGenerator:
    def setup_method(self):
        self.gen = ProblemGenerator(config=MagicMock(), console=MagicMock())

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_idea_generator_strategy(self, mock_config, mock_gen):
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="\\begin{solution}A\\end{solution}",
        )

        target = GenerationTarget(topic="mechanics", strategy="idea_generator")
        result = self.gen.generate(target, with_solution=True)

        assert isinstance(result, GeneratedProblemResult)
        assert result.strategy_used == "idea_generator"
        assert result.problem_tex == "\\item Q"
        mock_gen.assert_called_once()

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_idea_generator_no_solution(self, mock_config, mock_gen):
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        target = GenerationTarget(topic="optics", strategy="idea_generator")
        result = self.gen.generate(target, with_solution=False)

        assert result.solution_tex == ""
        assert result.combined_tex == "\\item Q"

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_tone_injection(self, mock_config, mock_gen):
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        target = GenerationTarget(topic="mechanics", strategy="idea_generator")
        self.gen.generate(target, with_solution=True, tone="symmetry-heavy")

        call_kwargs = mock_gen.call_args
        ideas = call_kwargs.kwargs.get("ideas")
        # The tone should be resolved from TONE_PRESETS for physics → full description
        assert any("Exploit symmetry" in idea for idea in ideas)

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_freeform_tone_injection(self, mock_config, mock_gen):
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        target = GenerationTarget(topic="mechanics", strategy="idea_generator")
        self.gen.generate(target, with_solution=True, tone="focus on energy and symmetry")

        call_kwargs = mock_gen.call_args
        ideas = call_kwargs.kwargs.get("ideas")
        assert any("focus on energy and symmetry" in idea for idea in ideas)

    @patch("vbagent.config.get_config")
    def test_cross_topic_strategy(self, mock_config):
        """Cross-topic delegates to analyze + generate variant agents."""
        mock_config.return_value.subject = "physics"
        mock_config.return_value.base_url = ""

        # Mock at the generator instance level to avoid triggering module-level agent creation
        # in vbagent.agents.variants which calls apply_provider_config()
        target = GenerationTarget(topic="optics", strategy="cross_topic")
        mock_result = GeneratedProblemResult(
            problem_tex="\\item Cross-topic Q", solution_tex="",
            combined_tex="\\item Cross-topic Q", target=target,
            strategy_used="cross_topic",
        )
        with patch.object(self.gen, "_via_cross_topic", return_value=mock_result):
            result = self.gen.generate(target, seed_problems=["\\item Source Q"])

        assert result.strategy_used == "cross_topic"
        assert result.problem_tex == "\\item Cross-topic Q"

    @patch("vbagent.agents.classification.problem_combiner.combine_problems")
    def test_combiner_strategy(self, mock_combine):
        mock_combine.return_value = MagicMock(
            combined_problem_latex="\\item Combined",
            combined_solution_latex="\\begin{solution}Combined\\end{solution}",
        )

        target = GenerationTarget(topic="mechanics", strategy="combiner")
        result = self.gen.generate(target, seed_problems=["\\item Q1", "\\item Q2"])

        assert result.strategy_used == "combiner"
        assert "Combined" in result.problem_tex
        mock_combine.assert_called_once()

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_combiner_fallback_to_idea_gen_with_insufficient_seeds(self, mock_config, mock_gen):
        """Combiner needs >= 2 seeds; with 1 seed it falls back to idea_generator."""
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        target = GenerationTarget(topic="mechanics", strategy="combiner")
        result = self.gen.generate(target, seed_problems=["\\item Q1"])

        assert result.strategy_used == "idea_generator"

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_seed_ideas_passed_through(self, mock_config, mock_gen):
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        target = GenerationTarget(
            topic="mechanics", strategy="idea_generator",
            seed_ideas=["projectile on incline"],
        )
        self.gen.generate(target, with_solution=True)

        call_kwargs = mock_gen.call_args
        ideas = call_kwargs.kwargs.get("ideas")
        assert "projectile on incline" in ideas

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_no_tone_means_no_prefix(self, mock_config, mock_gen):
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        target = GenerationTarget(topic="mechanics", strategy="idea_generator")
        self.gen.generate(target, with_solution=True, tone="")

        call_kwargs = mock_gen.call_args
        ideas = call_kwargs.kwargs.get("ideas")
        # No tone prefix should be added
        assert not any("[Tone:" in idea for idea in ideas)
