"""SyllabusManager — extraction, coverage analysis, target selection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import (
    CoverageReport,
    GenerationTarget,
    ProblemEntry,
    Syllabus,
    SyllabusSubtopic,
    SyllabusTopic,
    TopicCoverage,
    VALID_DIFFICULTIES,
)


class SyllabusManager:
    """Builds and maintains the syllabus tree, analyzes coverage gaps."""

    def __init__(self, syllabus: Optional[Syllabus] = None):
        self.syllabus = syllabus

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        path.write_text(self.syllabus.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "SyllabusManager":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(syllabus=Syllabus.model_validate(data))

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def extract_from_problems(
        self, problem_files: list[Path], subject: str,
    ) -> Syllabus:
        """Build syllabus tree from existing .tex files using classification agents."""
        from vbagent.agents.classification.unified_classifier import classify_unified
        from vbagent.agents.classification.difficulty_assessor import assess_difficulty

        topic_map: dict[str, SyllabusTopic] = {}

        for file_path in problem_files:
            tex = file_path.read_text(encoding="utf-8")
            try:
                classification = classify_unified(str(file_path))
                topic_name = getattr(classification, "topic", None) or "uncategorized"
                subtopic_name = getattr(classification, "subtopic", None) or "general"
                diff = "medium"
                try:
                    d = assess_difficulty(tex, classification)
                    diff = getattr(d, "difficulty", "medium")
                except Exception:
                    pass
                concepts = getattr(classification, "key_concepts", []) or []
            except Exception:
                topic_name, subtopic_name, diff, concepts = "uncategorized", "general", "medium", []

            if topic_name not in topic_map:
                topic_map[topic_name] = SyllabusTopic(name=topic_name)
            topic = topic_map[topic_name]
            topic.current_count += 1

            sub = next((s for s in topic.subtopics if s.name == subtopic_name), None)
            if sub is None:
                sub = SyllabusSubtopic(name=subtopic_name)
                topic.subtopics.append(sub)
            sub.current_count += 1
            sub.concepts = list(set(sub.concepts + list(concepts)))
            sub.difficulty_distribution[diff] = sub.difficulty_distribution.get(diff, 0) + 1

        self.syllabus = Syllabus(
            subject=subject,
            topics=list(topic_map.values()),
            created_from="extracted",
            total_target=len(problem_files),
        )
        return self.syllabus

    # ------------------------------------------------------------------
    # Coverage analysis
    # ------------------------------------------------------------------

    def analyze_coverage(self, existing_problems: list[ProblemEntry]) -> CoverageReport:
        if not self.syllabus:
            return CoverageReport(overall_coverage_pct=0.0)

        topic_coverages: list[TopicCoverage] = []
        all_diffs = {d: 0 for d in VALID_DIFFICULTIES}

        for topic in self.syllabus.topics:
            matching = [p for p in existing_problems if p.topic == topic.name]
            current = len(matching)
            target = topic.target_count or max(current, 1)

            diff_dist = {d: 0 for d in VALID_DIFFICULTIES}
            for p in matching:
                d = p.difficulty if p.difficulty in VALID_DIFFICULTIES else "medium"
                diff_dist[d] += 1
                all_diffs[d] += 1

            ideal = max(1, target // 3)
            missing_diffs = [d for d, c in diff_dist.items() if c < ideal]
            covered_subs = {p.subtopic for p in matching}
            all_subs = {s.name for s in topic.subtopics}
            missing_subs = list(all_subs - covered_subs)

            pct = min((current / target * 100) if target > 0 else 0.0, 100.0)
            topic_coverages.append(TopicCoverage(
                topic=topic.name, target=target, current=current,
                coverage_pct=pct, missing_difficulties=missing_diffs,
                missing_subtopics=missing_subs,
            ))

        total_target = sum(tc.target for tc in topic_coverages)
        total_current = sum(tc.current for tc in topic_coverages)
        overall = min((total_current / total_target * 100) if total_target > 0 else 0.0, 100.0)

        recommended = []
        for tc in sorted(topic_coverages, key=lambda t: t.coverage_pct):
            if tc.coverage_pct < 100.0:
                recommended.append(GenerationTarget(
                    topic=tc.topic,
                    subtopic=tc.missing_subtopics[0] if tc.missing_subtopics else "",
                    difficulty=tc.missing_difficulties[0] if tc.missing_difficulties else "medium",
                    strategy="idea_generator",
                ))

        return CoverageReport(
            overall_coverage_pct=overall,
            topic_coverages=topic_coverages,
            difficulty_distribution=all_diffs,
            recommended_targets=recommended,
        )

    def select_next_target(self, coverage: CoverageReport) -> GenerationTarget:
        if coverage.recommended_targets:
            return coverage.recommended_targets[0]
        return GenerationTarget(topic="general")

    def update_after_generation(self, entry: ProblemEntry) -> None:
        if not self.syllabus:
            return
        for topic in self.syllabus.topics:
            if topic.name == entry.topic:
                topic.current_count += 1
                for sub in topic.subtopics:
                    if sub.name == entry.subtopic:
                        sub.current_count += 1
                        d = entry.difficulty if entry.difficulty in VALID_DIFFICULTIES else "medium"
                        sub.difficulty_distribution[d] = sub.difficulty_distribution.get(d, 0) + 1
                        break
                break
