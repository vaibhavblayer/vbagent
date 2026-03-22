"""Tests for paper orchestrator data models.

Covers: round-trip serialization, validation rules, tone presets registry.
"""

import pytest
from vbagent.paper.models import (
    CoverageReport,
    GeneratedProblemResult,
    GenerationReport,
    GenerationTarget,
    HintReport,
    HintResult,
    PaperState,
    ProblemEntry,
    QACheckResult,
    QAResult,
    SolutionReport,
    Syllabus,
    SyllabusSubtopic,
    SyllabusTopic,
    TopicCoverage,
    TONE_PRESETS,
    ALL_TONE_PRESETS,
    VALID_SUBJECTS,
    VALID_DIFFICULTIES,
)


# ---------------------------------------------------------------------------
# Syllabus models
# ---------------------------------------------------------------------------

class TestSyllabusModels:
    def test_syllabus_subtopic_defaults(self):
        sub = SyllabusSubtopic(name="kinematics")
        assert sub.name == "kinematics"
        assert sub.concepts == []
        assert sub.difficulty_distribution == {}
        assert sub.current_count == 0

    def test_syllabus_subtopic_difficulty_validation(self):
        with pytest.raises(ValueError, match="Invalid difficulty key"):
            SyllabusSubtopic(name="x", difficulty_distribution={"impossible": 1})

    def test_syllabus_topic_defaults(self):
        topic = SyllabusTopic(name="mechanics")
        assert topic.subtopics == []
        assert topic.target_count == 0
        assert topic.current_count == 0

    def test_syllabus_subject_validation(self):
        s = Syllabus(subject="Physics")  # should lowercase
        assert s.subject == "physics"

        with pytest.raises(ValueError, match="Invalid subject"):
            Syllabus(subject="history")

    def test_syllabus_round_trip(self):
        syllabus = Syllabus(
            subject="physics",
            topics=[
                SyllabusTopic(
                    name="mechanics",
                    subtopics=[SyllabusSubtopic(name="kinematics", concepts=["velocity", "acceleration"])],
                    target_count=5,
                    current_count=2,
                ),
            ],
            total_target=5,
        )
        json_str = syllabus.model_dump_json()
        restored = Syllabus.model_validate_json(json_str)
        assert restored.subject == "physics"
        assert len(restored.topics) == 1
        assert restored.topics[0].subtopics[0].concepts == ["velocity", "acceleration"]


# ---------------------------------------------------------------------------
# ProblemEntry & PaperState
# ---------------------------------------------------------------------------

class TestProblemEntry:
    def test_valid_entry(self):
        entry = ProblemEntry(
            serial=1, filename="Problem_1.tex", subject="physics", topic="mechanics",
        )
        assert entry.serial == 1
        assert entry.qa_status == "pending"
        assert entry.solution_status == "none"

    def test_serial_must_be_positive(self):
        with pytest.raises(ValueError, match="serial must be >= 1"):
            ProblemEntry(serial=0, filename="Problem_0.tex", subject="physics", topic="x")

    def test_filename_must_be_tex(self):
        with pytest.raises(ValueError, match="filename must end with .tex"):
            ProblemEntry(serial=1, filename="Problem_1.pdf", subject="physics", topic="x")

    def test_round_trip(self):
        entry = ProblemEntry(
            serial=5, filename="Problem_5.tex", subject="chemistry",
            topic="organic", subtopic="alkenes", difficulty="hard",
            question_type="mcq_sc", concepts=["addition", "markovnikov"],
            source="generated", qa_status="passed", solution_status="inline",
        )
        restored = ProblemEntry.model_validate_json(entry.model_dump_json())
        assert restored.serial == 5
        assert restored.concepts == ["addition", "markovnikov"]


class TestPaperState:
    def test_defaults(self):
        state = PaperState(paper_id="abc123", subject="physics")
        assert state.base_dir == "agentic"
        assert state.problems == []
        assert state.tone == ""
        assert state.serial_numbering is True

    def test_tone_field(self):
        state = PaperState(paper_id="t1", subject="physics", tone="symmetry-heavy")
        assert state.tone == "symmetry-heavy"

    def test_update_timestamp(self):
        state = PaperState(paper_id="t2", subject="physics")
        old_ts = state.updated_at
        state.update_timestamp()
        assert state.updated_at >= old_ts

    def test_round_trip_with_problems(self):
        state = PaperState(
            paper_id="test123", subject="mathematics", tone="competition-style",
            problems=[
                ProblemEntry(serial=1, filename="Problem_1.tex", subject="mathematics", topic="algebra"),
                ProblemEntry(serial=2, filename="Problem_2.tex", subject="mathematics", topic="calculus"),
            ],
        )
        restored = PaperState.model_validate_json(state.model_dump_json())
        assert len(restored.problems) == 2
        assert restored.tone == "competition-style"


# ---------------------------------------------------------------------------
# GenerationTarget & Coverage
# ---------------------------------------------------------------------------

class TestGenerationTarget:
    def test_defaults(self):
        t = GenerationTarget(topic="optics")
        assert t.difficulty == "medium"
        assert t.strategy == "idea_generator"
        assert t.seed_ideas == []

    def test_all_strategies(self):
        for s in ("idea_generator", "cross_topic", "combiner"):
            t = GenerationTarget(topic="x", strategy=s)
            assert t.strategy == s


class TestCoverageReport:
    def test_empty_report(self):
        r = CoverageReport(overall_coverage_pct=0.0)
        assert r.topic_coverages == []
        assert r.recommended_targets == []

    def test_round_trip(self):
        r = CoverageReport(
            overall_coverage_pct=75.0,
            topic_coverages=[TopicCoverage(topic="mechanics", target=10, current=7, coverage_pct=70.0)],
            difficulty_distribution={"easy": 2, "medium": 3, "hard": 2},
            recommended_targets=[GenerationTarget(topic="mechanics", difficulty="hard")],
        )
        restored = CoverageReport.model_validate_json(r.model_dump_json())
        assert restored.overall_coverage_pct == 75.0
        assert len(restored.recommended_targets) == 1


# ---------------------------------------------------------------------------
# Generation results
# ---------------------------------------------------------------------------

class TestGenerationResults:
    def test_generated_problem_result(self):
        r = GeneratedProblemResult(
            problem_tex="\\item Q", solution_tex="\\begin{solution}A\\end{solution}",
            combined_tex="\\item Q\n\n\\begin{solution}A\\end{solution}",
            target=GenerationTarget(topic="optics"), strategy_used="idea_generator",
        )
        assert r.strategy_used == "idea_generator"

    def test_generation_report(self):
        r = GenerationReport(total_requested=5, total_generated=4, total_passed_qa=3)
        assert r.total_generated == 4

    def test_solution_report(self):
        r = SolutionReport(total=3, solved=2, failed=1)
        assert r.solved + r.failed == r.total


# ---------------------------------------------------------------------------
# QA models
# ---------------------------------------------------------------------------

class TestQAModels:
    def test_qa_check_result(self):
        c = QACheckResult(checker="format", passed=True)
        assert c.auto_fixed is False

    def test_qa_result_aggregation(self):
        r = QAResult(
            passed=False,
            checks=[
                QACheckResult(checker="format", passed=True),
                QACheckResult(checker="clarity", passed=False, issues=["unclear"]),
            ],
        )
        assert not r.passed
        assert len(r.checks) == 2


# ---------------------------------------------------------------------------
# Hint models
# ---------------------------------------------------------------------------

class TestHintModels:
    def test_hint_result(self):
        h = HintResult(hint_text="Think about energy conservation", hint_style="conceptual", key_concept="energy")
        assert h.hint_style == "conceptual"

    def test_hint_report(self):
        r = HintReport(total=5, generated=4, failed=1)
        assert r.generated + r.failed == r.total


# ---------------------------------------------------------------------------
# Tone presets
# ---------------------------------------------------------------------------

class TestTonePresets:
    def test_all_subjects_have_presets(self):
        for subj in ("physics", "chemistry", "mathematics"):
            assert subj in TONE_PRESETS
            assert len(TONE_PRESETS[subj]) >= 3

    def test_preset_values_are_nonempty_strings(self):
        for subj, presets in TONE_PRESETS.items():
            for name, desc in presets.items():
                assert isinstance(name, str) and len(name) > 0
                assert isinstance(desc, str) and len(desc) > 10, f"Preset {subj}/{name} has too short description"

    def test_all_tone_presets_flat_set(self):
        assert "symmetry-heavy" in ALL_TONE_PRESETS
        assert "mechanistic" in ALL_TONE_PRESETS
        assert "competition-style" in ALL_TONE_PRESETS

    def test_no_duplicate_preset_names_within_subject(self):
        for subj, presets in TONE_PRESETS.items():
            names = list(presets.keys())
            assert len(names) == len(set(names)), f"Duplicate preset names in {subj}"

    @pytest.mark.parametrize("subject", ["physics", "chemistry", "mathematics"])
    def test_subject_specific_presets(self, subject):
        presets = TONE_PRESETS[subject]
        assert len(presets) >= 3
        # Each preset name should be kebab-case-ish (lowercase, hyphens)
        for name in presets:
            assert name == name.lower(), f"Preset name {name} should be lowercase"
