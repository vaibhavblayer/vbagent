"""IdeaStore — persistent, deduplicated idea repository.

JSON-backed store that supports:
- Adding ideas with automatic deduplication
- Auto-tagging lenses on ingest
- Querying by topic, subject, lens compatibility
- Tracking combinations to prevent duplicates
- Generating systematic IDs (PHY-MAG-001)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from vbagent.ideas.models import (
    Idea,
    CombinationRecord,
    IdeaStore as IdeaStoreModel,
    SUBJECT_CODES,
    TOPIC_CODES,
)
from vbagent.ideas.tagger import tag_lenses


class IdeaStore:
    """Manages a persistent idea store backed by a JSON file."""

    def __init__(self, path: Path, subject: str = "physics"):
        self.path = Path(path)
        self.subject = subject
        self._store: IdeaStoreModel = self._load()

    def _load(self) -> IdeaStoreModel:
        """Load store from disk, or create empty."""
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                return IdeaStoreModel.model_validate(data)
            except (json.JSONDecodeError, Exception):
                pass
        return IdeaStoreModel(subject=self.subject)

    def save(self) -> None:
        """Persist store to disk."""
        self._update_stats()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._store.model_dump(), indent=2, ensure_ascii=False)
        )

    def _update_stats(self) -> None:
        """Refresh stats dict."""
        topics = set(i.topic for i in self._store.ideas if i.topic)
        self._store.stats = {
            "total_ideas": len(self._store.ideas),
            "topics": len(topics),
            "topic_list": sorted(topics),
            "total_combinations": len(self._store.combinations),
            "last_updated": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # ID generation
    # ------------------------------------------------------------------

    def _next_id(self, topic: str) -> str:
        """Generate next systematic ID for a topic.

        Format: {SUB}-{TOP}-{NNN}
        e.g. PHY-MAG-001
        """
        sub_code = SUBJECT_CODES.get(self.subject, "UNK")
        top_code = TOPIC_CODES.get(topic.lower().strip(), "GEN")

        counter_key = f"{sub_code}-{top_code}"
        n = self._store.counters.get(counter_key, 0) + 1
        self._store.counters[counter_key] = n

        return f"{sub_code}-{top_code}-{n:03d}"

    def _next_combo_id(self, topic: str) -> str:
        """Generate next combination ID.

        Format: VBP-{SUB}-{TOP}-{NNN}
        """
        sub_code = SUBJECT_CODES.get(self.subject, "UNK")
        top_code = TOPIC_CODES.get(topic.lower().strip(), "GEN")

        counter_key = f"combo-{sub_code}-{top_code}"
        n = self._store.counters.get(counter_key, 0) + 1
        self._store.counters[counter_key] = n

        return f"VBP-{sub_code}-{top_code}-{n:03d}"

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _signature_exists(self, sig: str) -> Optional[Idea]:
        """Check if an idea with this signature already exists."""
        for idea in self._store.ideas:
            if idea.signature() == sig:
                return idea
        return None

    # ------------------------------------------------------------------
    # Adding ideas
    # ------------------------------------------------------------------

    def add(self, idea: Idea, auto_tag: bool = True) -> tuple[Idea, bool]:
        """Add an idea to the store with deduplication.

        Returns (idea, is_new). If duplicate, merges sources and returns
        the existing idea with is_new=False.
        """
        if auto_tag:
            idea = tag_lenses(idea)

        sig = idea.signature()
        existing = self._signature_exists(sig)

        if existing:
            # Merge sources
            for src in idea.sources:
                if src not in existing.sources:
                    existing.sources.append(src)
            # Merge formulas
            for f in idea.formulas:
                if f not in existing.formulas:
                    existing.formulas.append(f)
            return existing, False

        # New idea — assign ID
        if not idea.id:
            idea.id = self._next_id(idea.topic)
        idea.subject = self.subject
        self._store.ideas.append(idea)
        return idea, True

    def add_many(self, ideas: list[Idea], auto_tag: bool = True) -> tuple[int, int]:
        """Add multiple ideas. Returns (new_count, duplicate_count)."""
        new_count = 0
        dup_count = 0
        for idea in ideas:
            _, is_new = self.add(idea, auto_tag=auto_tag)
            if is_new:
                new_count += 1
            else:
                dup_count += 1
        return new_count, dup_count

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    @property
    def ideas(self) -> list[Idea]:
        """All ideas in the store."""
        return self._store.ideas

    @property
    def combinations(self) -> list[CombinationRecord]:
        """All combination records."""
        return self._store.combinations

    def count(self) -> int:
        return len(self._store.ideas)

    def by_topic(self, topic: str) -> list[Idea]:
        """Get ideas filtered by topic."""
        topic = topic.lower().strip()
        return [i for i in self._store.ideas if i.topic.lower().strip() == topic]

    def by_lens(self, lens: str, include_compatible: bool = True) -> list[Idea]:
        """Get ideas that support a given lens."""
        results = []
        for idea in self._store.ideas:
            if lens in idea.natural_lenses:
                results.append(idea)
            elif include_compatible and lens in idea.compatible_lenses:
                results.append(idea)
        return results

    def by_topic_and_lens(
        self, topic: str, lens: str, include_compatible: bool = True
    ) -> list[Idea]:
        """Filter by both topic and lens."""
        topic = topic.lower().strip()
        return [
            i for i in self.by_lens(lens, include_compatible)
            if i.topic.lower().strip() == topic
        ]

    def topics(self) -> list[str]:
        """List all unique topics."""
        return sorted(set(i.topic for i in self._store.ideas if i.topic))

    # ------------------------------------------------------------------
    # Combination tracking
    # ------------------------------------------------------------------

    def combo_exists(
        self, idea_ids: list[str], lenses: list[str] | None = None
    ) -> bool:
        """Check if this exact combination has been generated before.

        If lenses is None, checks idea_ids only.
        If lenses is provided, checks idea_ids + lenses together.
        """
        sorted_ids = sorted(idea_ids)
        sorted_lenses = sorted(lenses) if lenses else None

        for combo in self._store.combinations:
            if sorted(combo.idea_ids) == sorted_ids:
                if sorted_lenses is None:
                    return True
                if sorted(combo.lenses_used) == sorted_lenses:
                    return True
        return False

    def log_combination(self, record: CombinationRecord) -> None:
        """Log a generated combination."""
        if not record.combo_id:
            # Infer topic from first idea
            first_idea = self.get_by_id(record.idea_ids[0]) if record.idea_ids else None
            topic = first_idea.topic if first_idea else "general"
            record.combo_id = self._next_combo_id(topic)
        self._store.combinations.append(record)

    def get_by_id(self, idea_id: str) -> Optional[Idea]:
        """Look up an idea by its ID."""
        for idea in self._store.ideas:
            if idea.id == idea_id:
                return idea
        return None
