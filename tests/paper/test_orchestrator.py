"""Tests for PaperOrchestrator — standalone and syllabus-driven flows."""

from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest

from vbagent.paper.orchestrator import PaperOrchestrator
from vbagent.paper.manifest import PaperManifest
from vbagent.paper.generator import ProblemGenerator
from vbagent.paper.qa import QAPipeline
from vbagent.paper.syllabus import SyllabusManager
from vbagent.paper.models import (
    GeneratedProblemResult,
    GenerationTarget,
    PaperState,
    ProblemEntry,
    QAResult,
    QACheckResult,
    CoverageReport,
    HintResult,
)


@pytest.fixture
def orch_env(tmp_path):
    """Set up an orchestrator with tmp_path, bypassing lazy config/console imports."""
    config = MagicMock()
    config.subject = "physics"
    console = MagicMock()

    # Construct directly, passing config and console to skip lazy imports
    orch = PaperOrchestrator.__new__(PaperOrchestrator)
    orch.base_dir = tmp_path
    orch.config = config
    orch.console = console
    orch.manifest = PaperManifest(tmp_path)
    orch.generator = ProblemGenerator(config, console)
    orch.qa_pipeline = QAPipeline(config, console)
    orch.syllabus_mgr = SyllabusManager()

    return orch, tmp_path, config, console


class TestOrchestratorInit:
    def test_init_paper_creates_manifest(self, orch_env):
        orch, tmp_path, _, _ = orch_env
        state = orch.init_paper(source_dir=None, subject="physics")
        assert isinstance(state, PaperState)
        assert state.subject == "physics"
        assert (tmp_path / "manifest.json").exists()

    def test_init_paper_with_existing_tex(self, orch_env):
        orch, tmp_path, _, _ = orch_env
        source = tmp_path / "source"
        source.mkdir()
        (source / "Problem_1.tex").write_text("\\item Q1")
        (source / "Problem_2.tex").write_text("\\item Q2")

        # Mock syllabus extraction since it calls real classification agents
        from vbagent.paper.models import Syllabus
        mock_syllabus = Syllabus(subject="physics", total_target=2)
        with patch.object(orch.syllabus_mgr, "extract_from_problems", return_value=mock_syllabus), \
             patch.object(orch.syllabus_mgr, "save"):
            state = orch.init_paper(source_dir=source, subject="physics")
        assert len(state.problems) == 2
        assert all(p.source == "scanned" for p in state.problems)

    def test_init_paper_no_overwrite_without_force(self, orch_env):
        orch, tmp_path, _, _ = orch_env
        state1 = orch.init_paper(source_dir=None, subject="physics")
        state2 = orch.init_paper(source_dir=None, subject="chemistry")
        # Without force, should return existing state
        assert state2.paper_id == state1.paper_id

    def test_init_paper_force_overwrites(self, orch_env):
        orch, tmp_path, _, _ = orch_env
        orch.init_paper(source_dir=None, subject="physics")
        state2 = orch.init_paper(source_dir=None, subject="chemistry", force=True)
        assert state2.subject == "chemistry"


class TestStandaloneGeneration:
    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_generate_standalone_basic(self, mock_config, mock_gen, orch_env):
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Electrostatics Q",
            solution_latex="\\begin{solution}A\\end{solution}",
        )

        result = orch.generate_standalone(topic="electrostatics", question_type="mcq_sc")

        assert isinstance(result, GeneratedProblemResult)
        assert result.strategy_used == "idea_generator"
        scans = tmp_path / "scans"
        assert scans.exists()
        tex_files = list(scans.glob("Problem_*.tex"))
        assert len(tex_files) == 1

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_generate_standalone_no_solution(self, mock_config, mock_gen, orch_env):
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        result = orch.generate_standalone(topic="optics", with_solution=False)
        assert result.solution_tex == ""

        state = orch.manifest.load()
        assert state.problems[-1].solution_status == "none"

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_generate_standalone_with_tone(self, mock_config, mock_gen, orch_env):
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        # Set paper-level tone
        state = orch.manifest.load()
        state.tone = "energy-methods"
        orch.manifest.save(state)

        orch.generate_standalone(topic="mechanics")

        call_kwargs = mock_gen.call_args
        ideas = call_kwargs.kwargs.get("ideas")
        # Should contain the resolved tone description for "energy-methods"
        assert any("energy" in idea.lower() for idea in ideas)

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_generate_standalone_tone_override(self, mock_config, mock_gen, orch_env):
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        # Set paper-level tone
        state = orch.manifest.load()
        state.tone = "energy-methods"
        orch.manifest.save(state)

        # Override with explicit tone
        orch.generate_standalone(topic="mechanics", tone="conceptual")

        call_kwargs = mock_gen.call_args
        ideas = call_kwargs.kwargs.get("ideas")
        # Should use the override "conceptual" (resolved), not paper-level "energy-methods"
        assert any("Qualitative" in idea or "conceptual" in idea.lower() for idea in ideas)

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_serial_increments(self, mock_config, mock_gen, orch_env):
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        orch.generate_standalone(topic="mechanics")
        orch.generate_standalone(topic="optics")

        state = orch.manifest.load()
        serials = [p.serial for p in state.problems]
        assert serials == [1, 2]


class TestStatus:
    def test_get_status_empty(self, orch_env):
        orch, _, _, _ = orch_env
        state = orch.get_status()
        assert isinstance(state, PaperState)
        assert len(state.problems) == 0

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_get_status_after_generation(self, mock_config, mock_gen, orch_env):
        orch, _, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        orch.generate_standalone(topic="mechanics")
        state = orch.get_status()
        assert len(state.problems) == 1


class TestQA:
    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_run_qa(self, mock_config, mock_gen, orch_env):
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        orch.generate_standalone(topic="mechanics")

        # Mock the qa_pipeline.run at the instance level to avoid importing quality agents
        from vbagent.paper.models import QAResult, QACheckResult
        mock_qa_result = QAResult(
            passed=True,
            checks=[
                QACheckResult(checker="format", passed=True),
                QACheckResult(checker="clarity", passed=True),
                QACheckResult(checker="grammar", passed=True),
            ],
        )
        with patch.object(orch.qa_pipeline, "run", return_value=mock_qa_result):
            results = orch.run_qa()
        assert len(results) == 1
        assert results[0]["passed"] is True


class TestHints:
    @patch("vbagent.agents.base.run_agent_sync")
    @patch("vbagent.agents.base.create_agent")
    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_generate_hints(self, mock_config, mock_gen, mock_create, mock_run, orch_env):
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )
        mock_create.return_value = MagicMock()
        mock_run.return_value = HintResult(
            hint_text="Think about energy conservation",
            hint_style="conceptual",
            key_concept="energy",
        )

        # Patch classification so it doesn't interfere with the HintResult mock
        with patch.object(orch, "_classify_generated", return_value=None):
            orch.generate_standalone(topic="mechanics")
        report = orch.generate_hints(hint_style="conceptual")

        assert report.generated == 1
        hint_dir = tmp_path / "hints"
        assert hint_dir.exists()
        hint_files = list(hint_dir.glob("*.tex"))
        assert len(hint_files) == 1


class TestPostGenClassification:
    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_standalone_enriches_entry(self, mock_config, mock_gen, orch_env):
        """generate_standalone should classify and fill subtopic/concepts."""
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Lagrangian bead problem", solution_latex="sol",
        )

        from vbagent.paper.models import PostGenClassification
        fake_class = PostGenClassification(
            subtopic="Lagrangian mechanics",
            concepts=["Lagrangian", "constraints", "generalized coordinates"],
            difficulty="hard",
            question_type="subjective",
            brief_description="Bead on rotating hoop",
        )
        with patch.object(orch, "_classify_generated", return_value=fake_class):
            orch.generate_standalone(topic="mechanics")

        state = orch.manifest.load()
        entry = state.problems[0]
        assert entry.subtopic == "Lagrangian mechanics"
        assert "Lagrangian" in entry.concepts
        assert entry.difficulty == "hard"

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_standalone_classification_failure_is_graceful(self, mock_config, mock_gen, orch_env):
        """If classification fails, entry should still be saved with defaults."""
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        with patch.object(orch, "_classify_generated", return_value=None):
            orch.generate_standalone(topic="optics")

        state = orch.manifest.load()
        assert len(state.problems) == 1
        assert state.problems[0].subtopic == ""  # not enriched, but still saved

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_covered_subtopics_collected(self, mock_config, mock_gen, orch_env):
        """_covered_subtopics should return subtopics already in manifest for a topic."""
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        from vbagent.paper.models import PostGenClassification
        # Generate two problems with different subtopics
        for sub in ["Lagrangian mechanics", "projectile motion"]:
            fake = PostGenClassification(subtopic=sub, concepts=["c1"], difficulty="medium")
            with patch.object(orch, "_classify_generated", return_value=fake):
                orch.generate_standalone(topic="mechanics")

        state = orch.manifest.load()
        covered = orch._covered_subtopics(state, "mechanics")
        assert "Lagrangian mechanics" in covered
        assert "projectile motion" in covered

    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_avoid_subtopics_passed_to_generator(self, mock_config, mock_gen, orch_env):
        """When subtopics are already covered, diversity hint should appear in ideas."""
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        # Pre-populate a problem with a subtopic
        state = orch.manifest.load()
        state.subject = "physics"
        state.problems.append(ProblemEntry(
            serial=1, filename="Problem_1.tex", subject="physics",
            topic="mechanics", subtopic="Lagrangian mechanics", source="generated",
        ))
        orch.manifest.save(state)
        (tmp_path / "scans").mkdir(exist_ok=True)
        (tmp_path / "scans" / "Problem_1.tex").write_text("\\item Q1")

        with patch.object(orch, "_classify_generated", return_value=None):
            orch.generate_standalone(topic="mechanics")

        call_kwargs = mock_gen.call_args
        ideas = call_kwargs.kwargs.get("ideas", [])
        # The diversity hint should mention "Lagrangian mechanics" to avoid
        assert any("Lagrangian mechanics" in idea for idea in ideas)


class TestEnrich:
    @patch("vbagent.agents.classification.idea_generator.generate_from_idea")
    @patch("vbagent.config.get_config")
    def test_enrich_fills_empty_subtopics(self, mock_config, mock_gen, orch_env):
        orch, tmp_path, _, _ = orch_env
        mock_config.return_value.subject = "physics"
        mock_gen.return_value = MagicMock(
            problem_latex="\\item Q", solution_latex="sol",
        )

        # Generate a problem without classification
        with patch.object(orch, "_classify_generated", return_value=None):
            orch.generate_standalone(topic="mechanics")

        state = orch.manifest.load()
        assert state.problems[0].subtopic == ""

        # Now enrich
        from vbagent.paper.models import PostGenClassification
        fake = PostGenClassification(
            subtopic="rotational dynamics", concepts=["torque", "angular momentum"],
            difficulty="medium",
        )
        with patch.object(orch, "_classify_generated", return_value=fake):
            results = orch.enrich_problems()

        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["subtopic"] == "rotational dynamics"

        # Verify manifest was updated
        state = orch.manifest.load()
        assert state.problems[0].subtopic == "rotational dynamics"

    def test_enrich_skips_already_classified(self, orch_env):
        """enrich_problems with no ids should skip problems that already have subtopics."""
        orch, tmp_path, _, _ = orch_env
        state = orch.manifest.load()
        state.subject = "physics"
        state.problems.append(ProblemEntry(
            serial=1, filename="Problem_1.tex", subject="physics",
            topic="mechanics", subtopic="already classified", source="generated",
        ))
        orch.manifest.save(state)
        (tmp_path / "scans").mkdir(exist_ok=True)
        (tmp_path / "scans" / "Problem_1.tex").write_text("\\item Q")

        results = orch.enrich_problems()
        assert len(results) == 0  # nothing to enrich
