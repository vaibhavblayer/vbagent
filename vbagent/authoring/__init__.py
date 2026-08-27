"""Canonical syllabus-driven problem authoring.

This package owns the contracts shared by CLI, paper, chat, and batch
generation.  It deliberately keeps planning deterministic and free of agent
calls so a large run can be inspected before any tokens are spent.
"""

from vbagent.authoring.api import (
    AuthoringExecution,
    execute_authoring,
    execute_variants,
    plan_authoring,
    plan_variants,
)
from vbagent.authoring.application import (
    ArtifactResult,
    AuthoringApplication,
    AuthoringIntent,
    CatalogChapterSummary,
    CatalogInspectionResult,
    CatalogListResult,
    CatalogSearchMatch,
    CatalogSearchResult,
    CatalogTopicPageResult,
    EvidenceResult,
    ItemPageResult,
    PlanResult,
    ReviewResult,
    RunCommandResult,
    RunStatusResult,
    WorkerLogPage,
)
from vbagent.authoring.catalog import SyllabusCatalogLoader
from vbagent.authoring.models import (
    AcceptancePolicy,
    AuthoringPlan,
    AuthoringRequest,
    CatalogChapter,
    CatalogTopic,
    CognitiveLevel,
    DiagramPolicy,
    GenerationSpec,
    QuestionType,
    Representation,
    SourceKind,
    SyllabusCatalog,
    VariantFamily,
)
from vbagent.authoring.pipeline import AuthoringPipeline
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.results import AuthoredCandidate, CandidateStatus, GateResult
from vbagent.authoring.service import AuthoringRunService
from vbagent.authoring.store import AuthoringStore, ItemStatus, RunStatus

__all__ = [
    "AcceptancePolicy",
    "ArtifactResult",
    "AuthoredCandidate",
    "AuthoringApplication",
    "AuthoringExecution",
    "AuthoringIntent",
    "AuthoringPipeline",
    "AuthoringPlan",
    "AuthoringPlanner",
    "AuthoringRequest",
    "AuthoringRunService",
    "AuthoringStore",
    "CandidateStatus",
    "CatalogChapter",
    "CatalogChapterSummary",
    "CatalogInspectionResult",
    "CatalogListResult",
    "CatalogSearchMatch",
    "CatalogSearchResult",
    "CatalogTopicPageResult",
    "CatalogTopic",
    "CognitiveLevel",
    "DiagramPolicy",
    "EvidenceResult",
    "GateResult",
    "GenerationSpec",
    "ItemPageResult",
    "ItemStatus",
    "PlanResult",
    "QuestionType",
    "Representation",
    "ReviewResult",
    "RunCommandResult",
    "RunStatus",
    "RunStatusResult",
    "SourceKind",
    "SyllabusCatalog",
    "SyllabusCatalogLoader",
    "VariantFamily",
    "WorkerLogPage",
    "execute_authoring",
    "execute_variants",
    "plan_authoring",
    "plan_variants",
]
