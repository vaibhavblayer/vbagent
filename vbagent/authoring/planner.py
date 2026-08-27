"""Deterministic batch-wide coverage and variety planning."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from typing import Any

from vbagent.authoring.catalog import SyllabusCatalogLoader
from vbagent.authoring.models import (
    AuthoringPlan,
    AuthoringRequest,
    CognitiveLevel,
    DiagramPolicy,
    GenerationSpec,
    QuestionType,
    Representation,
    SourceKind,
    SyllabusCatalog,
    VariantFamily,
)

DEFAULT_LENSES: dict[str, dict[str, float]] = {
    "physics": {
        "conceptual": 1,
        "algebraic": 1,
        "calculus": 1,
        "graphical": 1,
        "estimation": 1,
        "symmetry": 1,
    },
    "chemistry": {
        "conceptual": 1,
        "mechanistic": 1,
        "quantitative": 1,
        "structural": 1,
        "thermodynamic": 1,
        "graphical": 1,
    },
    "mathematics": {
        "algebraic": 1,
        "geometric": 1,
        "calculus": 1,
        "coordinate": 1,
        "combinatorial": 1,
        "proof": 1,
    },
    "biology": {
        "conceptual": 1,
        "process": 1,
        "experimental": 1,
        "data-analysis": 1,
        "comparison": 1,
        "structure-function": 1,
    },
}

DEFAULT_CONSTRUCTIONS: dict[str, float] = {
    "single-concept": 2,
    "multi-concept": 2,
    "contextual": 1,
    "counterfactual": 1,
}


class AuthoringPlanner:
    """Allocate an entire authoring run before generation begins."""

    def __init__(self, catalog_loader: type[SyllabusCatalogLoader] = SyllabusCatalogLoader):
        self.catalog_loader = catalog_loader

    def load_catalog(self, request: AuthoringRequest) -> SyllabusCatalog:
        if request.syllabus_path:
            catalog = self.catalog_loader.load_file(
                request.syllabus_path,
                exam=request.exam,
                subject=request.subject,
            )
        else:
            catalog = self.catalog_loader.load_builtin(request.exam, request.subject)
        if request.expected_syllabus_version and catalog.version != request.expected_syllabus_version:
            raise ValueError(
                f"syllabus version mismatch: requested {request.expected_syllabus_version!r}, "
                f"loaded {catalog.version!r}"
            )
        return catalog

    def plan(self, request: AuthoringRequest, catalog: SyllabusCatalog | None = None) -> AuthoringPlan:
        catalog = catalog or self.load_catalog(request)
        if catalog.exam != request.exam or catalog.subject != request.subject:
            raise ValueError(
                f"catalog identity {catalog.exam}/{catalog.subject} does not match "
                f"request {request.exam}/{request.subject}"
            )
        requested_types = set(request.question_types)
        allowed_types = {question_type.value for question_type in catalog.allowed_question_types}
        unsupported_types = sorted(requested_types - allowed_types)
        if unsupported_types:
            source = (
                f" See the official exam pattern: {catalog.exam_pattern_source_url}"
                if catalog.exam_pattern_source_url
                else ""
            )
            raise ValueError(
                f"{catalog.exam}/{catalog.subject} does not allow question type(s): "
                f"{', '.join(unsupported_types)}; allowed: {', '.join(sorted(allowed_types))}."
                f"{source}"
            )

        targets = self.catalog_loader.resolve_topics(
            catalog,
            chapter=request.chapter,
            topics=request.topics,
        )
        if not targets:
            raise ValueError("authoring request resolved to no syllabus topics")

        topic_sequence = self._allocate_topics(targets, request)
        question_types = _choice_sequence(request.question_types, request.count, request.seed, "question_type")
        difficulties = _choice_sequence(request.difficulties, request.count, request.seed, "difficulty")
        cognitive_levels = _choice_sequence(request.cognitive_levels, request.count, request.seed, "cognitive")
        representations = _choice_sequence(request.representations, request.count, request.seed, "representation")
        lenses = _choice_sequence(
            request.reasoning_lenses or DEFAULT_LENSES[request.subject],
            request.count,
            request.seed,
            "reasoning_lens",
        )
        constructions = _choice_sequence(
            request.construction_families or DEFAULT_CONSTRUCTIONS,
            request.count,
            request.seed,
            "construction",
        )
        diagram_ordinals = set(
            _selected_ordinals(request.count, round(request.diagram_ratio * request.count), request.seed, "diagram")
        )
        variant_families = (
            _choice_sequence(request.variant_families, request.count, request.seed, "variant_family")
            if request.variant_parent_spec_id
            else [None] * request.count
        )

        provisional: list[dict[str, Any]] = []
        for index in range(request.count):
            chapter, topic = topic_sequence[index]
            provisional.append(
                {
                    "ordinal": index + 1,
                    "exam": request.exam,
                    "subject": request.subject,
                    "syllabus_version": catalog.version,
                    "syllabus_source_sha256": catalog.source_sha256,
                    "syllabus_source_url": catalog.source_url,
                    "syllabus_official_source_sha256": catalog.official_source_sha256,
                    "exam_pattern_description": catalog.exam_pattern_description,
                    "exam_pattern_source_url": catalog.exam_pattern_source_url,
                    "exam_pattern_source_sha256": catalog.exam_pattern_source_sha256,
                    "exam_pattern_verified_at": catalog.exam_pattern_verified_at,
                    "chapter_id": chapter.id,
                    "chapter": chapter.title,
                    "chapter_description": chapter.description,
                    "topic_id": topic.id,
                    "topic": topic.title,
                    "topic_description": topic.description,
                    "question_type": QuestionType(str(question_types[index])),
                    "difficulty": int(difficulties[index]),
                    "cognitive_level": CognitiveLevel(str(cognitive_levels[index])),
                    "representation": Representation(str(representations[index])),
                    "reasoning_lens": str(lenses[index]),
                    "construction_family": str(constructions[index]),
                    "diagram_policy": (
                        DiagramPolicy.REQUIRED if index + 1 in diagram_ordinals else DiagramPolicy.FORBIDDEN
                    ),
                    "passage_question_count": request.passage_question_count,
                    "required_concepts": tuple(request.required_concepts),
                    "forbidden_concepts": tuple(request.forbidden_concepts),
                    "seed_ideas": tuple(request.seed_ideas),
                    "tone": request.tone,
                    "random_seed": _derived_seed(request.seed, "item", index + 1),
                    "acceptance": request.acceptance,
                    "include_solution": request.include_solution,
                    "include_idea": request.include_idea,
                    "source_kind": (
                        SourceKind.VARIANT if request.variant_parent_spec_id else SourceKind.ORIGINAL
                    ),
                    "variant_family": (
                        VariantFamily(str(variant_families[index]))
                        if variant_families[index] is not None
                        else None
                    ),
                    "parent_spec_id": request.variant_parent_spec_id,
                    "lineage_root_spec_id": request.variant_lineage_root_spec_id,
                    "lineage_depth": (
                        request.variant_parent_depth + 1 if request.variant_parent_spec_id else 0
                    ),
                    "parent_problem_latex": request.variant_parent_latex,
                    "parent_artifact_sha256": request.variant_parent_artifact_sha256,
                }
            )

        request_payload = request.model_dump(mode="json")
        plan_payload = {
            "request": request_payload,
            "catalog_sha256": catalog.source_sha256,
            "catalog_contract": {
                "version": catalog.version,
                "source_url": catalog.source_url,
                "official_source_sha256": catalog.official_source_sha256,
                "verified_at": catalog.verified_at,
                "allowed_question_types": [
                    question_type.value for question_type in catalog.allowed_question_types
                ],
                "exam_pattern_description": catalog.exam_pattern_description,
                "exam_pattern_source_url": catalog.exam_pattern_source_url,
                "exam_pattern_source_sha256": catalog.exam_pattern_source_sha256,
                "exam_pattern_verified_at": catalog.exam_pattern_verified_at,
            },
            "items": [
                {key: value.value if hasattr(value, "value") else value for key, value in item.items() if key != "acceptance"}
                for item in provisional
            ],
        }
        plan_id = _hash_payload(plan_payload)
        items: list[GenerationSpec] = []
        for item in provisional:
            spec_payload = {
                **item,
                "plan_id": plan_id,
            }
            spec_id = _hash_payload(_jsonable(spec_payload))
            items.append(GenerationSpec(spec_id=spec_id, **item))

        distributions = {
            "chapter": _counts(item.chapter for item in items),
            "topic": _counts(item.topic_id for item in items),
            "question_type": _counts(item.question_type.value for item in items),
            "difficulty": _counts(str(item.difficulty) for item in items),
            "cognitive_level": _counts(item.cognitive_level.value for item in items),
            "representation": _counts(item.representation.value for item in items),
            "reasoning_lens": _counts(item.reasoning_lens for item in items),
            "construction_family": _counts(item.construction_family for item in items),
            "diagram_policy": _counts(item.diagram_policy.value for item in items),
            "source_kind": _counts(item.source_kind.value for item in items),
        }
        if request.variant_parent_spec_id:
            distributions["variant_family"] = _counts(item.variant_family.value for item in items)
        warnings: list[str] = []
        if request.count < len(targets):
            warnings.append(
                f"requested count {request.count} is smaller than {len(targets)} selected topics; "
                "not every topic can be covered"
            )
        if request.acceptance.human_review_required:
            warnings.append("human review is required before generated candidates can be accepted")

        # draft, independent solve, classification, answer adjudication,
        # specification alignment, difficulty assessment, and final review.
        estimated_calls = request.count * (7 if request.include_solution else 1) + sum(
            item.diagram_policy is DiagramPolicy.REQUIRED for item in items
        )
        return AuthoringPlan(
            plan_id=plan_id,
            request=request,
            catalog_version=catalog.version,
            catalog_source=catalog.source,
            catalog_source_url=catalog.source_url,
            catalog_official_source_sha256=catalog.official_source_sha256,
            catalog_verified_at=catalog.verified_at,
            allowed_question_types=catalog.allowed_question_types,
            exam_pattern_description=catalog.exam_pattern_description,
            exam_pattern_source_url=catalog.exam_pattern_source_url,
            exam_pattern_source_sha256=catalog.exam_pattern_source_sha256,
            exam_pattern_verified_at=catalog.exam_pattern_verified_at,
            catalog_source_sha256=catalog.source_sha256,
            items=tuple(items),
            distributions=distributions,
            estimated_agent_calls=estimated_calls,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _allocate_topics(targets, request: AuthoringRequest):
        counts: dict[str, int] = {}
        for chapter, topic in targets:
            counts[topic.id] = request.existing_accepted_counts.get(
                topic.id,
                request.existing_accepted_counts.get(topic.title, 0),
            )
        order = list(targets)
        random.Random(_derived_seed(request.seed, "topic-order", 0)).shuffle(order)
        order_rank = {topic.id: index for index, (_, topic) in enumerate(order)}
        planned: Counter[str] = Counter()
        sequence = []
        by_id = {topic.id: (chapter, topic) for chapter, topic in targets}
        for _ in range(request.count):
            topic_id = min(
                by_id,
                key=lambda item_id: (counts[item_id] + planned[item_id], order_rank[item_id]),
            )
            planned[topic_id] += 1
            sequence.append(by_id[topic_id])
        return sequence


def _choice_sequence(weights: dict[Any, float], count: int, seed: int, axis: str) -> list[Any]:
    allocations = _allocate_weights(weights, count)
    sequence = [choice for choice, choice_count in allocations.items() for _ in range(choice_count)]
    random.Random(_derived_seed(seed, axis, count)).shuffle(sequence)
    return sequence


def _allocate_weights(weights: dict[Any, float], count: int) -> dict[Any, int]:
    items = sorted(weights.items(), key=lambda item: str(item[0]))
    total = sum(weight for _, weight in items)
    exact = [(choice, count * weight / total) for choice, weight in items]
    allocations = {choice: math.floor(value) for choice, value in exact}
    remaining = count - sum(allocations.values())
    ranked = sorted(exact, key=lambda item: (-(item[1] - math.floor(item[1])), str(item[0])))
    for choice, _ in ranked[:remaining]:
        allocations[choice] += 1
    return allocations


def _selected_ordinals(total: int, selected: int, seed: int, axis: str) -> list[int]:
    ordinals = list(range(1, total + 1))
    random.Random(_derived_seed(seed, axis, total)).shuffle(ordinals)
    return ordinals[:selected]


def _derived_seed(seed: int, axis: str, ordinal: int) -> int:
    digest = hashlib.sha256(f"{seed}:{axis}:{ordinal}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _counts(values) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))
