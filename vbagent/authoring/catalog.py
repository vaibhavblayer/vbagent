"""Versioned syllabus loading and strict chapter/topic resolution."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from vbagent.authoring.models import (
    CatalogChapter,
    CatalogTopic,
    QuestionType,
    SyllabusCatalog,
)


class CatalogResolutionError(ValueError):
    """Raised when a passed chapter or topic cannot be resolved uniquely."""


def _parse_allowed_question_types(value: Any) -> tuple[QuestionType, ...]:
    if value is None:
        return tuple(QuestionType)
    if not isinstance(value, (list, tuple, set)):
        raise ValueError("allowed_question_types must be a list of canonical question type names")
    try:
        return tuple(QuestionType(str(item)) for item in value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in QuestionType)
        raise ValueError(f"invalid allowed question type; expected one of: {allowed}") from exc


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "unnamed"


def _normalize_exam(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _search_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _topic_aliases(title: str) -> tuple[str, ...]:
    fragments = re.split(r"[,;:]|\band\b", title, flags=re.IGNORECASE)
    aliases = {_search_key(fragment) for fragment in fragments}
    aliases.discard("")
    aliases.discard(_search_key(title))
    return tuple(sorted(aliases))


class SyllabusCatalogLoader:
    """Load built-in or user-provided syllabus snapshots."""

    DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "syllabus"
    BUILTIN_PROVENANCE: dict[tuple[str, str], dict[str, Any]] = {
        ("jee_main", "physics"): {
            "version": "2026.1",
            "source_url": (
                "https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/"
                "uploads/2025/10/202510311323551056.pdf"
            ),
            "verified_at": "2026-08-26",
            "allowed_question_types": ["mcq_sc", "integer"],
            "exam_pattern_description": (
                "JEE Main Paper 1 Physics uses four-option single-correct MCQs and "
                "numerical-value questions. Numerical answers are rounded to the nearest integer."
            ),
            "exam_pattern_source_url": (
                "https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/"
                "uploads/2025/11/202511021649722475.pdf"
            ),
            "exam_pattern_verified_at": "2026-08-26",
        },
        ("neet", "physics"): {
            "version": "2026.1",
            "source_url": (
                "https://www.nmc.org.in/MCIRest/open/getDocument?path=%2FDocuments%2FPublic%2F"
                "Portal%2FLatestNews%2FPublic+Notice_NEET_removed.pdf"
            ),
            "verified_at": "2026-08-26",
            "allowed_question_types": ["mcq_sc"],
            "exam_pattern_description": (
                "NEET (UG) Physics uses multiple-choice questions with four options "
                "and one correct or best answer."
            ),
            "exam_pattern_source_url": (
                "https://cdnbbsr.s3waas.gov.in/s37bc1ec1d9c3426357e69acd5bf320061/"
                "uploads/2026/02/202602231394640855.pdf"
            ),
            "exam_pattern_verified_at": "2026-08-26",
        },
    }

    @classmethod
    def available(cls) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        if not cls.DATA_DIR.exists():
            return pairs
        for exam_dir in sorted(path for path in cls.DATA_DIR.iterdir() if path.is_dir()):
            for syllabus_file in sorted(exam_dir.glob("*.json")):
                pairs.append((exam_dir.name, syllabus_file.stem))
        return pairs

    @classmethod
    def load_builtin(cls, exam: str, subject: str) -> SyllabusCatalog:
        exam_key = exam.strip().lower().replace("-", "_").replace(" ", "_")
        subject_key = subject.strip().lower()
        path = cls.DATA_DIR / exam_key / f"{subject_key}.json"
        if not path.is_file():
            available = ", ".join(f"{item_exam}/{item_subject}" for item_exam, item_subject in cls.available())
            raise FileNotFoundError(
                f"No built-in syllabus for {exam_key}/{subject_key}. "
                f"Available catalogs: {available or 'none'}. Pass syllabus_path for a custom catalog."
            )
        return cls.load_file(path, exam=exam_key, subject=subject_key)

    @classmethod
    def load_file(
        cls,
        path: str | Path,
        *,
        exam: str | None = None,
        subject: str | None = None,
    ) -> SyllabusCatalog:
        syllabus_path = Path(path).expanduser().resolve()
        raw = syllabus_path.read_bytes()
        source_sha256 = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw.decode("utf-8"))

        metadata: dict[str, Any] = {}
        chapters_data: Any = data
        if isinstance(data, dict) and "chapters" in data:
            metadata = data.get("metadata", {})
            chapters_data = data["chapters"]

        resolved_exam = _normalize_exam(
            exam or metadata.get("exam") or syllabus_path.parent.name
        )
        resolved_subject = (subject or metadata.get("subject") or syllabus_path.stem).strip().lower()
        if not resolved_exam or not resolved_subject:
            raise ValueError("custom syllabus must identify exam and subject")

        builtin_path = cls.DATA_DIR / resolved_exam / f"{resolved_subject}.json"
        is_builtin = syllabus_path == builtin_path.resolve()
        if not is_builtin and "allowed_question_types" not in metadata:
            raise ValueError(
                "custom syllabus metadata must declare allowed_question_types so exam "
                "formats are never guessed"
            )
        if not is_builtin and not str(metadata.get("exam_pattern_description", "")).strip():
            raise ValueError(
                "custom syllabus metadata must declare exam_pattern_description"
            )

        chapters = cls._parse_chapters(chapters_data, resolved_exam, resolved_subject)
        declared_version = metadata.get("version")
        version = str(declared_version) if declared_version else f"sha256:{source_sha256[:16]}"
        allowed_question_types = _parse_allowed_question_types(
            metadata.get("allowed_question_types")
        )
        catalog = SyllabusCatalog(
            exam=resolved_exam,
            subject=resolved_subject,
            version=version,
            source=str(syllabus_path),
            source_url=str(metadata.get("source_url", "")),
            verified_at=str(metadata.get("verified_at", "")),
            allowed_question_types=allowed_question_types,
            exam_pattern_description=str(metadata.get("exam_pattern_description", "")),
            exam_pattern_source_url=str(metadata.get("exam_pattern_source_url", "")),
            exam_pattern_verified_at=str(metadata.get("exam_pattern_verified_at", "")),
            source_sha256=source_sha256,
            chapters=tuple(chapters),
        )
        if is_builtin:
            provenance = cls.BUILTIN_PROVENANCE.get((resolved_exam, resolved_subject), {})
            catalog = catalog.model_copy(
                update={
                    "version": provenance.get("version", catalog.version),
                    "source_url": provenance.get("source_url", catalog.source_url),
                    "verified_at": provenance.get("verified_at", catalog.verified_at),
                    "allowed_question_types": _parse_allowed_question_types(
                        provenance.get("allowed_question_types")
                    ),
                    "exam_pattern_description": provenance.get(
                        "exam_pattern_description", catalog.exam_pattern_description
                    ),
                    "exam_pattern_source_url": provenance.get(
                        "exam_pattern_source_url", catalog.exam_pattern_source_url
                    ),
                    "exam_pattern_verified_at": provenance.get(
                        "exam_pattern_verified_at", catalog.exam_pattern_verified_at
                    ),
                }
            )
        return catalog

    @staticmethod
    def _parse_chapters(chapters_data: Any, exam: str, subject: str) -> list[CatalogChapter]:
        if isinstance(chapters_data, dict):
            entries = list(chapters_data.items())
        elif isinstance(chapters_data, list):
            entries = [(item.get("title") or item.get("name"), item) for item in chapters_data]
        else:
            raise ValueError("syllabus chapters must be an object or list")

        chapters: list[CatalogChapter] = []
        for chapter_index, (chapter_title, chapter_data) in enumerate(entries, 1):
            if not chapter_title or not isinstance(chapter_data, dict):
                raise ValueError(f"invalid chapter at position {chapter_index}")
            chapter_slug = _slug(str(chapter_title))
            chapter_id = str(chapter_data.get("id") or f"{exam}.{subject}.{chapter_slug}")
            topic_entries = chapter_data.get("topics", [])
            topics: list[CatalogTopic] = []
            for topic_index, topic_data in enumerate(topic_entries, 1):
                if isinstance(topic_data, str):
                    topic_title = topic_data
                    topic_description = ""
                    explicit_id = None
                    explicit_aliases: list[str] = []
                elif isinstance(topic_data, dict):
                    topic_title = topic_data.get("title") or topic_data.get("name")
                    topic_description = str(topic_data.get("description", ""))
                    explicit_id = topic_data.get("id")
                    explicit_aliases = list(topic_data.get("aliases", []))
                else:
                    raise ValueError(f"invalid topic in chapter {chapter_title!r}")
                if not topic_title:
                    raise ValueError(f"topic {topic_index} in {chapter_title!r} has no title")
                topic_id = str(explicit_id or f"{chapter_id}.topic-{topic_index:03d}")
                aliases = set(_topic_aliases(str(topic_title)))
                aliases.update(_search_key(alias) for alias in explicit_aliases if alias)
                topics.append(
                    CatalogTopic(
                        id=topic_id,
                        title=str(topic_title),
                        aliases=tuple(sorted(aliases)),
                        description=topic_description,
                    )
                )
            chapters.append(
                CatalogChapter(
                    id=chapter_id,
                    title=str(chapter_title),
                    description=str(chapter_data.get("description", "")),
                    topics=tuple(topics),
                )
            )
        return chapters

    @staticmethod
    def resolve_chapter(catalog: SyllabusCatalog, query: str) -> CatalogChapter:
        matches = _resolve_matches(
            query,
            catalog.chapters,
            lambda chapter: (chapter.id, chapter.title),
        )
        if len(matches) == 1:
            return matches[0]
        available = ", ".join(chapter.title for chapter in catalog.chapters)
        if not matches:
            raise CatalogResolutionError(f"chapter {query!r} not found; available chapters: {available}")
        names = ", ".join(chapter.title for chapter in matches)
        raise CatalogResolutionError(f"chapter {query!r} is ambiguous; matches: {names}")

    @classmethod
    def resolve_topics(
        cls,
        catalog: SyllabusCatalog,
        *,
        chapter: str | None = None,
        topics: list[str] | None = None,
    ) -> list[tuple[CatalogChapter, CatalogTopic]]:
        chapter_scope = [cls.resolve_chapter(catalog, chapter)] if chapter else list(catalog.chapters)
        all_topics = [(item_chapter, topic) for item_chapter in chapter_scope for topic in item_chapter.topics]
        if not topics:
            return all_topics

        resolved: list[tuple[CatalogChapter, CatalogTopic]] = []
        seen: set[str] = set()
        for query in topics:
            matches = _resolve_matches(
                query,
                all_topics,
                lambda pair: (pair[1].id, pair[1].title, *pair[1].aliases),
            )
            if not matches:
                scope = f"chapter {chapter!r}" if chapter else f"{catalog.exam}/{catalog.subject}"
                raise CatalogResolutionError(f"topic {query!r} not found in {scope}")
            if len(matches) > 1:
                names = ", ".join(f"{item_chapter.title}: {topic.title}" for item_chapter, topic in matches)
                raise CatalogResolutionError(f"topic {query!r} is ambiguous; matches: {names}")
            item_chapter, topic = matches[0]
            if topic.id not in seen:
                seen.add(topic.id)
                resolved.append((item_chapter, topic))
        return resolved


def _resolve_matches(query: str, items: list[Any] | tuple[Any, ...], values) -> list[Any]:
    needle = _search_key(query)
    if not needle:
        return []
    exact = [item for item in items if needle in {_search_key(value) for value in values(item)}]
    if exact:
        return exact
    return [
        item
        for item in items
        if any(needle in _search_key(value) or _search_key(value) in needle for value in values(item))
    ]
