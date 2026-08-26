"""Tests for paper consumption, enrichment, and post-authoring workflows."""

from unittest.mock import MagicMock, patch

import pytest

from vbagent.paper.models import HintResult, PaperState, ProblemEntry
from vbagent.paper.orchestrator import PaperOrchestrator


@pytest.fixture
def orch_env(tmp_path):
    config = MagicMock(subject="physics")
    console = MagicMock()
    orch = PaperOrchestrator(base_dir=tmp_path, config=config, console=console)
    return orch, tmp_path, config, console


def _add_problem(
    orch: PaperOrchestrator,
    tex: str = r"\item A physics problem.",
    *,
    subtopic: str = "",
    solution_status: str = "none",
) -> ProblemEntry:
    state = orch.manifest.load()
    serial = orch.manifest.get_next_serial(state)
    entry = ProblemEntry(
        serial=serial,
        filename=f"Problem_{serial}.tex",
        subject="physics",
        topic="mechanics",
        subtopic=subtopic,
        solution_status=solution_status,
    )
    orch._save_problem(tex, entry.filename)
    state.problems.append(entry)
    orch.manifest.save(state)
    return entry


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
        (source / "Problem_1.tex").write_text(r"\item Q1", encoding="utf-8")
        (source / "Problem_2.tex").write_text(r"\item Q2", encoding="utf-8")

        from vbagent.paper.models import Syllabus

        mock_syllabus = Syllabus(subject="physics", total_target=2)
        with patch.object(
            orch.syllabus_mgr, "extract_from_problems", return_value=mock_syllabus
        ), patch.object(orch.syllabus_mgr, "save"):
            state = orch.init_paper(source_dir=source, subject="physics")

        assert len(state.problems) == 2
        assert all(problem.source == "scanned" for problem in state.problems)

    def test_init_paper_does_not_overwrite_without_force(self, orch_env):
        orch, _, _, _ = orch_env
        first = orch.init_paper(source_dir=None, subject="physics")
        second = orch.init_paper(source_dir=None, subject="chemistry")
        assert second.paper_id == first.paper_id
        assert second.subject == "physics"

    def test_init_paper_force_updates_subject(self, orch_env):
        orch, _, _, _ = orch_env
        orch.init_paper(source_dir=None, subject="physics")
        state = orch.init_paper(source_dir=None, subject="chemistry", force=True)
        assert state.subject == "chemistry"

    def test_legacy_creation_routes_are_removed(self, orch_env):
        orch, _, _, _ = orch_env
        assert hasattr(orch, "author_problems")
        assert not hasattr(orch, "generate_standalone")
        assert not hasattr(orch, "generate_problems")
        assert not hasattr(orch, "generate_batch")


class TestStatus:
    def test_get_status_empty(self, orch_env):
        orch, _, _, _ = orch_env
        assert orch.get_status().problems == []

    def test_get_status_after_imported_problem(self, orch_env):
        orch, _, _, _ = orch_env
        _add_problem(orch)
        assert len(orch.get_status().problems) == 1


class TestIndependentSolutions:
    @patch("vbagent.agents.orchestration.solution_orchestrator.SolutionOrchestrator.run")
    def test_generate_solutions_preserves_final_answer(self, mock_run, orch_env):
        from vbagent.agents.orchestration.solution_orchestrator import SolutionResult

        orch, tmp_path, _, _ = orch_env
        entry = _add_problem(orch, r"\item Find the equilibrium.")
        answer = r"Stable: $C$; unstable: $A$, $E$."
        mock_run.return_value = SolutionResult(
            latex=(
                r"\item Find the equilibrium."
                "\n\\begin{solution}\nWork.\n\\end{solution}"
                f"\n\\begin{{finalanswer}}\n{answer}\n\\end{{finalanswer}}"
            ),
            answer_type="subjective",
            final_answer_latex=answer,
        )

        report = orch.generate_solutions(problem_ids=[entry.serial])

        assert report.solved == 1
        scan_content = (tmp_path / "scans" / entry.filename).read_text(encoding="utf-8")
        solution_content = (tmp_path / "solutions" / entry.filename).read_text(
            encoding="utf-8"
        )
        assert f"\\begin{{finalanswer}}\n    {answer}" in scan_content
        assert r"\begin{finalanswer}" in solution_content

    def test_regenerate_selects_already_generated_solutions(self, orch_env):
        orch, _, _, _ = orch_env
        _add_problem(orch, solution_status="generated")
        with patch(
            "vbagent.agents.orchestration.solution_orchestrator.SolutionOrchestrator.run",
            side_effect=RuntimeError("called"),
        ) as run:
            report = orch.generate_solutions(regenerate=True)

        run.assert_called_once()
        assert report.total == 1


class TestQA:
    def test_run_qa(self, orch_env):
        from vbagent.paper.models import QACheckResult, QAResult

        orch, _, _, _ = orch_env
        entry = _add_problem(orch)
        result = QAResult(
            passed=True,
            checks=[QACheckResult(checker="format", passed=True)],
        )
        with patch.object(orch.qa_pipeline, "run", return_value=result):
            results = orch.run_qa(problem_ids=[entry.serial])

        assert results == [{"serial": entry.serial, "passed": True, "issues": [[]]}]
        assert orch.manifest.load().problems[0].qa_status == "passed"


class TestHints:
    @patch("vbagent.agents.base.run_agent_sync")
    @patch("vbagent.agents.base.create_agent")
    def test_generate_hints(self, mock_create, mock_run, orch_env):
        orch, tmp_path, _, _ = orch_env
        entry = _add_problem(orch)
        mock_create.return_value = MagicMock()
        mock_run.return_value = HintResult(
            hint_text="Think about energy conservation",
            hint_style="conceptual",
            key_concept="energy",
        )

        report = orch.generate_hints(problem_ids=[entry.serial], hint_style="conceptual")

        assert report.generated == 1
        assert (tmp_path / "hints" / entry.filename).exists()
        scan = (tmp_path / "scans" / entry.filename).read_text(encoding="utf-8")
        assert r"\begin{hint}" in scan


class TestEnrich:
    def test_enrich_fills_empty_subtopics(self, orch_env):
        from vbagent.paper.models import PostGenClassification

        orch, _, _, _ = orch_env
        _add_problem(orch)
        classification = PostGenClassification(
            subtopic="rotational dynamics",
            concepts=["torque", "angular momentum"],
            difficulty="medium",
        )
        with patch.object(orch, "_classify_generated", return_value=classification):
            results = orch.enrich_problems()

        assert results[0]["success"] is True
        assert results[0]["subtopic"] == "rotational dynamics"
        assert orch.manifest.load().problems[0].subtopic == "rotational dynamics"

    def test_enrich_skips_already_classified(self, orch_env):
        orch, _, _, _ = orch_env
        _add_problem(orch, subtopic="already classified")
        assert orch.enrich_problems() == []
