"""Canonical syllabus-driven problem authoring.

This package owns the contracts shared by CLI, paper, chat, and batch
generation.  It deliberately keeps planning deterministic and free of agent
calls so a large run can be inspected before any tokens are spent.
"""

from vbagent.authoring.catalog import SyllabusCatalogLoader
from vbagent.authoring.api import (
    AuthoringExecution,
    execute_authoring,
    execute_variants,
    plan_authoring,
)
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
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.pipeline import AuthoringPipeline
from vbagent.authoring.results import AuthoredCandidate, CandidateStatus, GateResult
from vbagent.authoring.service import AuthoringRunService
from vbagent.authoring.store import AuthoringStore, ItemStatus, RunStatus

__all__ = [
    "AcceptancePolicy",
    "AuthoringPlan",
    "AuthoringExecution",
    "AuthoringPlanner",
    "AuthoringPipeline",
    "AuthoringRequest",
    "AuthoringRunService",
    "AuthoringStore",
    "CatalogChapter",
    "CatalogTopic",
    "CandidateStatus",
    "CognitiveLevel",
    "DiagramPolicy",
    "GenerationSpec",
    "GateResult",
    "ItemStatus",
    "QuestionType",
    "Representation",
    "RunStatus",
    "SourceKind",
    "SyllabusCatalog",
    "SyllabusCatalogLoader",
    "VariantFamily",
    "AuthoredCandidate",
    "execute_authoring",
    "execute_variants",
    "plan_authoring",
]
