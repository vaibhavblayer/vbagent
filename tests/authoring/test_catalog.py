import json

import pytest

from vbagent.authoring.catalog import CatalogResolutionError, SyllabusCatalogLoader


def test_builtin_catalog_has_stable_ids_and_provenance():
    catalog = SyllabusCatalogLoader.load_builtin("jee-main", "physics")

    assert catalog.exam == "jee_main"
    assert catalog.subject == "physics"
    assert catalog.version == "2026.1"
    assert catalog.source_url.startswith("https://")
    assert catalog.official_source_sha256 == (
        "7cad9da2a12065444828f744bd9f1a93a2dd0d9bd54c32a6d92d94a769e4f905"
    )
    assert catalog.verified_at == "2026-08-27"
    assert len(catalog.source_sha256) == 64
    assert catalog.chapters[0].id == "jee_main.physics.physics-and-measurement"
    assert catalog.chapters[0].topics[0].id.endswith(".topic-001")


def test_all_official_2026_subject_catalogs_are_available():
    expected = {
        ("jee_main", "chemistry"): (20, {"mcq_sc", "integer"}),
        ("jee_main", "mathematics"): (14, {"mcq_sc", "integer"}),
        ("jee_main", "physics"): (20, {"mcq_sc", "integer"}),
        ("neet", "biology"): (10, {"mcq_sc"}),
        ("neet", "chemistry"): (20, {"mcq_sc"}),
        ("neet", "physics"): (20, {"mcq_sc"}),
    }

    assert set(SyllabusCatalogLoader.available()) == set(expected)
    for (exam, subject), (chapter_count, question_types) in expected.items():
        catalog = SyllabusCatalogLoader.load_builtin(exam, subject)
        assert catalog.version == "2026.1"
        assert catalog.verified_at == "2026-08-27"
        assert catalog.exam_pattern_verified_at == "2026-08-27"
        assert len(catalog.chapters) == chapter_count
        assert all(chapter.topics for chapter in catalog.chapters)
        assert {item.value for item in catalog.allowed_question_types} == question_types
        assert catalog.source_url.startswith("https://")
        assert catalog.exam_pattern_source_url.startswith("https://")
        assert len(catalog.official_source_sha256) == 64
        assert len(catalog.exam_pattern_source_sha256) == 64


def test_greatest_integer_function_resolves_to_official_simple_functions_scope():
    catalog = SyllabusCatalogLoader.load_builtin("jee_main", "mathematics")

    chapter, topic = SyllabusCatalogLoader.resolve_topics(
        catalog,
        chapter="limit continuity and differentiability",
        topics=["greatest integer function"],
    )[0]

    assert chapter.title == "LIMIT, CONTINUITY AND DIFFERENTIABILITY"
    assert topic.title == "Real-valued functions, algebra of functions and graphs of simple functions"
    assert "floor function" in topic.aliases


def test_resolves_passed_chapter_and_partial_topic():
    catalog = SyllabusCatalogLoader.load_builtin("jee_main", "physics")

    resolved = SyllabusCatalogLoader.resolve_topics(
        catalog,
        chapter="kinematics",
        topics=["projectile motion"],
    )

    assert len(resolved) == 1
    chapter, topic = resolved[0]
    assert chapter.title == "KINEMATICS"
    assert "Projectile Motion" in topic.title


def test_ambiguous_topic_is_rejected_instead_of_silently_selected():
    catalog = SyllabusCatalogLoader.load_builtin("jee_main", "physics")

    with pytest.raises(CatalogResolutionError, match="ambiguous"):
        SyllabusCatalogLoader.resolve_topics(catalog, topics=["motion"])


def test_missing_builtin_lists_actual_catalogs():
    with pytest.raises(FileNotFoundError, match="Available catalogs"):
        SyllabusCatalogLoader.load_builtin("jee_advanced", "mathematics")


def test_versioned_custom_catalog(tmp_path):
    path = tmp_path / "custom.json"
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "exam": "school_exam",
                    "subject": "mathematics",
                    "version": "2026.1",
                    "allowed_question_types": ["subjective"],
                    "exam_pattern_description": "Open-response questions with written working.",
                },
                "chapters": [
                    {
                        "id": "algebra",
                        "title": "Algebra",
                        "topics": [
                            {"id": "quadratics", "title": "Quadratic equations", "aliases": ["quadratic"]}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    catalog = SyllabusCatalogLoader.load_file(path)

    assert catalog.exam == "school_exam"
    assert catalog.subject == "mathematics"
    assert catalog.version == "2026.1"
    assert [item.value for item in catalog.allowed_question_types] == ["subjective"]
    assert SyllabusCatalogLoader.resolve_topics(catalog, topics=["quadratic"])[0][1].id == "quadratics"


def test_custom_catalog_fails_closed_without_exam_format_metadata(tmp_path):
    path = tmp_path / "custom.json"
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "exam": "school_exam",
                    "subject": "mathematics",
                    "version": "2026.1",
                },
                "chapters": [
                    {
                        "title": "Algebra",
                        "topics": ["Quadratic equations"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="allowed_question_types"):
        SyllabusCatalogLoader.load_file(path)
