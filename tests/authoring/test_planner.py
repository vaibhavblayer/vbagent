import pytest
from pydantic import ValidationError

from vbagent.authoring.models import AcceptancePolicy, AuthoringRequest, DiagramPolicy
from vbagent.authoring.planner import AuthoringPlanner


def _request(**updates):
    values = {
        "exam": "jee_main",
        "subject": "physics",
        "chapter": "kinematics",
        "count": 12,
        "question_types": {"mcq_sc": 2, "integer": 1},
        "difficulties": {4: 1, 6: 1, 8: 1},
        "diagram_ratio": 0.25,
        "seed": 42,
    }
    values.update(updates)
    return AuthoringRequest(**values)


def test_planner_allocates_full_batch_before_generation():
    plan = AuthoringPlanner().plan(_request())

    assert len(plan.items) == 12
    assert plan.distributions["question_type"] == {"integer": 4, "mcq_sc": 8}
    assert plan.distributions["difficulty"] == {"4": 4, "6": 4, "8": 4}
    assert plan.distributions["diagram_policy"][DiagramPolicy.REQUIRED.value] == 3
    assert sum(plan.distributions["topic"].values()) == 12
    assert all(item.exam == "jee_main" for item in plan.items)
    assert all(item.chapter == "KINEMATICS" for item in plan.items)
    assert all(item.fingerprint() for item in plan.items)


def test_plan_is_reproducible_and_seed_changes_assignment():
    planner = AuthoringPlanner()
    first = planner.plan(_request())
    second = planner.plan(_request())
    changed = planner.plan(_request(seed=43))

    assert first.plan_id == second.plan_id
    assert first.items == second.items
    assert first.plan_id != changed.plan_id
    assert first.items != changed.items


def test_existing_accepted_coverage_fills_least_covered_topics_first():
    planner = AuthoringPlanner()
    catalog = planner.load_catalog(_request(count=1))
    targets = planner.catalog_loader.resolve_topics(catalog, chapter="kinematics")
    counts = {topic.id: 10 for _, topic in targets}
    least_topic = targets[-1][1]
    counts[least_topic.id] = 0

    plan = planner.plan(_request(count=1, existing_accepted_counts=counts), catalog)

    assert plan.items[0].topic_id == least_topic.id


def test_requested_topic_is_authoritative():
    plan = AuthoringPlanner().plan(_request(count=3, topics=["projectile motion"]))

    assert len({item.topic_id for item in plan.items}) == 1
    assert all("Projectile Motion" in item.topic for item in plan.items)


def test_invalid_contracts_fail_preflight():
    with pytest.raises(ValidationError, match="unsupported question types"):
        _request(question_types={"essayish": 1})
    with pytest.raises(ValidationError, match="difficulty levels"):
        _request(difficulties={11: 1})
    with pytest.raises(ValidationError, match="positive weight"):
        _request(question_types={"mcq_sc": 0})


def test_expected_catalog_version_prevents_silent_drift():
    with pytest.raises(ValueError, match="syllabus version mismatch"):
        AuthoringPlanner().plan(_request(expected_syllabus_version="old-version"))


def test_builtin_exam_profiles_reject_unsupported_formats_before_generation():
    planner = AuthoringPlanner()

    jee = planner.plan(_request(question_types={"mcq_sc": 1, "integer": 1}))
    assert jee.allowed_question_types == ("mcq_sc", "integer")
    assert "nearest integer" in jee.exam_pattern_description
    assert jee.exam_pattern_source_url.startswith("https://")

    neet_request = _request(
        exam="neet",
        question_types={"integer": 1},
        count=1,
        topics=["projectile motion"],
    )
    with pytest.raises(ValueError, match="does not allow question type.*integer"):
        planner.plan(neet_request)


def test_custom_catalog_question_type_profile_is_enforced(tmp_path):
    catalog = tmp_path / "school.json"
    catalog.write_text(
        """{
          "metadata": {
            "exam": "school_exam",
            "subject": "physics",
            "version": "2026.1",
            "allowed_question_types": ["subjective"],
            "exam_pattern_description": "Written open-response questions.",
            "exam_pattern_source_url": "https://example.edu/pattern.pdf",
            "exam_pattern_verified_at": "2026-08-26"
          },
          "chapters": [{
            "id": "motion",
            "title": "Motion",
            "topics": [{"id": "speed", "title": "Speed"}]
          }]
        }""",
        encoding="utf-8",
    )
    request = AuthoringRequest(
        exam="school_exam",
        subject="physics",
        chapter="motion",
        topics=["speed"],
        syllabus_path=str(catalog),
        question_types={"mcq_sc": 1},
    )

    with pytest.raises(ValueError, match="allowed: subjective"):
        AuthoringPlanner().plan(request)


def test_acceptance_gates_cannot_be_disabled_programmatically():
    mandatory = [
        "require_structure_check",
        "require_independent_solution",
        "require_answer_agreement",
        "require_syllabus_check",
        "require_difficulty_check",
        "require_compile",
        "require_review",
        "require_novelty_check",
    ]
    for field in mandatory:
        with pytest.raises(ValidationError):
            AcceptancePolicy(**{field: False})


def test_exam_profile_provenance_is_part_of_plan_identity():
    planner = AuthoringPlanner()
    request = _request(count=1, question_types={"mcq_sc": 1})
    catalog = planner.load_catalog(request)
    first = planner.plan(request, catalog)
    changed = planner.plan(
        request,
        catalog.model_copy(update={"exam_pattern_verified_at": "2099-01-01"}),
    )

    assert first.plan_id != changed.plan_id
