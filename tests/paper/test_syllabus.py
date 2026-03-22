"""Tests for SyllabusManager — coverage analysis and target selection."""

import pytest
from pathlib import Path

from vbagent.paper.syllabus import SyllabusManager
from vbagent.paper.models import (
    CoverageReport,
    GenerationTarget,
    ProblemEntry,
    Syllabus,
    SyllabusSubtopic,
    SyllabusTopic,
)


def _make_syllabus() -> Syllabus:
    """Helper: create a test syllabus with 2 topics."""
    return Syllabus(
        subject="physics",
        topics=[
            SyllabusTopic(
                name="mechanics",
                subtopics=[
                    SyllabusSubtopic(name="kinematics", difficulty_distribution={"easy": 1, "medium": 1}),
                    SyllabusSubtopic(name="dynamics", difficulty_distribution={"medium": 1}),
                ],
                target_count=6,
                current_count=3,
            ),
            SyllabusTopic(
                name="optics",
                subtopics=[
                    SyllabusSubtopic(name="reflection"),
                    SyllabusSubtopic(name="refraction"),
                ],
                target_count=4,
                current_count=1,
            ),
        ],
        total_target=10,
    )


def _make_entry(serial, topic, subtopic="", difficulty="medium") -> ProblemEntry:
    return ProblemEntry(
        serial=serial, filename=f"Problem_{serial}.tex",
        subject="physics", topic=topic, subtopic=subtopic, difficulty=difficulty,
    )


class TestSyllabusManager:
    def test_analyze_coverage_empty_problems(self):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        report = mgr.analyze_coverage([])
        assert report.overall_coverage_pct == 0.0
        assert len(report.topic_coverages) == 2

    def test_analyze_coverage_partial(self):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        problems = [
            _make_entry(1, "mechanics", "kinematics", "easy"),
            _make_entry(2, "mechanics", "kinematics", "medium"),
            _make_entry(3, "mechanics", "dynamics", "hard"),
            _make_entry(4, "optics", "reflection", "medium"),
        ]
        report = mgr.analyze_coverage(problems)
        assert 0 < report.overall_coverage_pct < 100.0
        assert len(report.topic_coverages) == 2

        mech = next(tc for tc in report.topic_coverages if tc.topic == "mechanics")
        assert mech.current == 3
        assert mech.target == 6
        assert mech.coverage_pct == 50.0

        opt = next(tc for tc in report.topic_coverages if tc.topic == "optics")
        assert opt.current == 1
        assert opt.target == 4

    def test_analyze_coverage_full(self):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        problems = [_make_entry(i, "mechanics") for i in range(1, 7)] + \
                   [_make_entry(i, "optics") for i in range(7, 11)]
        report = mgr.analyze_coverage(problems)
        assert report.overall_coverage_pct == 100.0

    def test_analyze_coverage_no_syllabus(self):
        mgr = SyllabusManager()
        report = mgr.analyze_coverage([])
        assert report.overall_coverage_pct == 0.0

    def test_difficulty_distribution(self):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        problems = [
            _make_entry(1, "mechanics", difficulty="easy"),
            _make_entry(2, "mechanics", difficulty="easy"),
            _make_entry(3, "optics", difficulty="hard"),
        ]
        report = mgr.analyze_coverage(problems)
        assert report.difficulty_distribution["easy"] == 2
        assert report.difficulty_distribution["hard"] == 1
        assert report.difficulty_distribution["medium"] == 0

    def test_recommended_targets_sorted_by_coverage(self):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        problems = [
            _make_entry(1, "mechanics"),
            _make_entry(2, "mechanics"),
            _make_entry(3, "mechanics"),
        ]
        report = mgr.analyze_coverage(problems)
        # Optics has 0 problems → lower coverage → should be first recommendation
        assert len(report.recommended_targets) >= 1
        assert report.recommended_targets[0].topic == "optics"

    def test_select_next_target_from_recommendations(self):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        report = CoverageReport(
            overall_coverage_pct=50.0,
            recommended_targets=[
                GenerationTarget(topic="optics", difficulty="hard"),
                GenerationTarget(topic="mechanics", difficulty="easy"),
            ],
        )
        target = mgr.select_next_target(report)
        assert target.topic == "optics"
        assert target.difficulty == "hard"

    def test_select_next_target_fallback(self):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        report = CoverageReport(overall_coverage_pct=100.0)
        target = mgr.select_next_target(report)
        assert target.topic == "general"

    def test_update_after_generation(self):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        entry = _make_entry(10, "mechanics", "kinematics", "hard")
        mgr.update_after_generation(entry)

        topic = next(t for t in mgr.syllabus.topics if t.name == "mechanics")
        assert topic.current_count == 4  # was 3
        sub = next(s for s in topic.subtopics if s.name == "kinematics")
        assert sub.current_count == 1
        assert sub.difficulty_distribution.get("hard", 0) == 1

    def test_save_and_load(self, tmp_path):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        path = tmp_path / "syllabus.json"
        mgr.save(path)

        loaded = SyllabusManager.load(path)
        assert loaded.syllabus.subject == "physics"
        assert len(loaded.syllabus.topics) == 2
        assert loaded.syllabus.topics[0].name == "mechanics"

    def test_missing_subtopics_detection(self):
        mgr = SyllabusManager(syllabus=_make_syllabus())
        # Only cover "reflection" in optics, "refraction" should be missing
        problems = [_make_entry(1, "optics", "reflection")]
        report = mgr.analyze_coverage(problems)
        opt = next(tc for tc in report.topic_coverages if tc.topic == "optics")
        assert "refraction" in opt.missing_subtopics
