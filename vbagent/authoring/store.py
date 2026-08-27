"""Durable SQLite ledger and atomic artifacts for large authoring runs."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterator

from vbagent.authoring.models import AuthoringPlan, AuthoringRequest, GenerationSpec
from vbagent.authoring.novelty import NoveltyIndex
from vbagent.authoring.paths import (
    generated_artifact_path,
    generated_build_path,
    generated_manifest_path,
    generated_output_root,
)
from vbagent.authoring.results import (
    REQUIRED_ACCEPTANCE_GATES,
    AuthoredCandidate,
    CandidateStatus,
)
from vbagent.authoring.structure import validate_final_structure

_POST_DRAFT_STAGES = (
    "validating_draft_structure",
    "generating_problem_diagram",
    "solving_independently",
    "validating_final_structure",
    "classifying_problem",
    "adjudicating_answer",
    "checking_syllabus_alignment",
    "assessing_difficulty",
    "compiling_item",
    "reviewing_quality",
    "checking_novelty",
    "finalizing_item",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _validate_stage(stage: str) -> str:
    normalized = stage.strip()
    if not normalized or len(normalized) > 80:
        raise ValueError("authoring stage must contain between 1 and 80 characters")
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_" for character in normalized):
        raise ValueError("authoring stage must use lowercase snake_case")
    return normalized


def _process_is_alive(pid: int | None) -> bool:
    """Best-effort liveness check for a worker launched on this host."""
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _dispatch_is_active(
    run: sqlite3.Row | dict[str, Any],
    dispatch: sqlite3.Row | dict[str, Any] | None,
    *,
    now_text: str,
    cutoff: str,
) -> bool:
    if not dispatch or dispatch["status"] not in {"launching", "started"}:
        return False
    active_lease = bool(
        run["lease_owner"]
        and run["lease_expires_at"]
        and run["lease_expires_at"] > now_text
    )
    if active_lease or dispatch["updated_at"] > cutoff:
        return True
    return dispatch["status"] == "started" and _process_is_alive(dispatch["pid"])


def _finalize_usage_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    """Derive cache percentages from merged per-profile/domain counters."""
    input_tokens = int(bucket.get("input_tokens", 0) or 0)
    cached_tokens = int(bucket.get("cached_tokens", 0) or 0)
    write_tokens = int(bucket.get("cache_write_tokens", 0) or 0)
    reported_requests = int(bucket.get("cache_reported_requests", 0) or 0)
    bucket["cache_hit_percent"] = round(
        cached_tokens / input_tokens * 100, 2
    ) if input_tokens else 0.0
    bucket["cache_write_percent"] = round(
        write_tokens / input_tokens * 100, 2
    ) if input_tokens else 0.0
    bucket["cache_request_hit_percent"] = (
        round(
            int(bucket.get("cache_read_requests", 0) or 0)
            / reported_requests
            * 100,
            2,
        )
        if reported_requests
        else None
    )
    eligible_tokens = int(bucket.get("effective_input_eligible_tokens", 0) or 0)
    bucket["effective_input_multiplier"] = (
        round(
            float(bucket.get("effective_input_cost_units", 0.0) or 0.0)
            / input_tokens,
            4,
        )
        if input_tokens and eligible_tokens == input_tokens
        else None
    )
    return bucket


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ItemStatus(str, Enum):
    PENDING = "pending"
    LEASED = "leased"
    ACCEPTED = "accepted"
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_ITEM_STATUSES = {
    ItemStatus.ACCEPTED.value,
    ItemStatus.DRAFT.value,
    ItemStatus.NEEDS_REVIEW.value,
    ItemStatus.REJECTED.value,
    ItemStatus.FAILED.value,
    ItemStatus.CANCELLED.value,
}


@dataclass(frozen=True)
class ClaimedItem:
    run_id: str
    spec: GenerationSpec
    attempt: int
    max_attempts: int
    output_dir: Path
    lease_owner: str
    retry_reason: str | None = None


class AuthoringStore:
    """Transactional run/item state separate from the image batch schema."""

    DB_NAME = ".vbagent_authoring.db"

    def __init__(self, path: str | Path):
        requested = Path(path).expanduser()
        explicit_database = requested.suffix.lower() in {".db", ".sqlite", ".sqlite3"}
        self.db_path = (requested if explicit_database else requested / self.DB_NAME).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30,
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self._create_schema()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def __enter__(self) -> "AuthoringStore":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
            except Exception:
                self.conn.rollback()
                raise
            else:
                self.conn.commit()

    def _create_schema(self) -> None:
        with self._lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS authoring_runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    plan_sha256 TEXT NOT NULL,
                    catalog_version TEXT NOT NULL,
                    catalog_source_sha256 TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    concurrency INTEGER NOT NULL,
                    cancel_reason TEXT,
                    current_stage TEXT,
                    stage_updated_at TEXT,
                    lease_owner TEXT,
                    lease_expires_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS authoring_items (
                    spec_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES authoring_runs(run_id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    exam TEXT,
                    subject TEXT,
                    chapter_id TEXT,
                    topic_id TEXT,
                    question_type TEXT,
                    parent_spec_id TEXT,
                    problem_latex TEXT,
                    projection_version INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL,
                    next_attempt_at TEXT NOT NULL,
                    lease_owner TEXT,
                    lease_expires_at TEXT,
                    last_candidate_json TEXT,
                    error_stage TEXT,
                    error_message TEXT,
                    retry_reason TEXT,
                    artifact_dir TEXT,
                    artifact_sha256 TEXT,
                    human_review_reason TEXT,
                    current_stage TEXT,
                    stage_updated_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(run_id, ordinal)
                );

                CREATE INDEX IF NOT EXISTS idx_authoring_items_claim
                ON authoring_items(run_id, status, next_attempt_at, ordinal);

                CREATE INDEX IF NOT EXISTS idx_authoring_items_status
                ON authoring_items(run_id, status);

                CREATE TABLE IF NOT EXISTS authoring_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    spec_id TEXT NOT NULL REFERENCES authoring_items(spec_id) ON DELETE CASCADE,
                    attempt INTEGER NOT NULL,
                    candidate_status TEXT NOT NULL,
                    candidate_json TEXT NOT NULL,
                    artifact_dir TEXT,
                    artifact_sha256 TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(spec_id, attempt)
                );

                CREATE TABLE IF NOT EXISTS authoring_gates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    spec_id TEXT NOT NULL REFERENCES authoring_items(spec_id) ON DELETE CASCADE,
                    attempt INTEGER NOT NULL,
                    gate_order INTEGER NOT NULL,
                    gate TEXT NOT NULL,
                    required INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    summary TEXT,
                    data_json TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    UNIQUE(spec_id, attempt, gate_order)
                );

                CREATE TABLE IF NOT EXISTS authoring_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    spec_id TEXT NOT NULL REFERENCES authoring_items(spec_id) ON DELETE CASCADE,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS authoring_exports (
                    source_spec_id TEXT PRIMARY KEY REFERENCES authoring_items(spec_id),
                    current_spec_id TEXT NOT NULL REFERENCES authoring_items(spec_id),
                    output_root TEXT NOT NULL,
                    number INTEGER NOT NULL CHECK(number > 0),
                    content_sha256 TEXT,
                    metadata_json TEXT,
                    UNIQUE(output_root, number)
                );
                CREATE INDEX IF NOT EXISTS idx_authoring_exports_current
                ON authoring_exports(current_spec_id);

                CREATE TABLE IF NOT EXISTS authoring_dispatches (
                    run_id TEXT PRIMARY KEY REFERENCES authoring_runs(run_id) ON DELETE CASCADE,
                    dispatch_token TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pid INTEGER,
                    resume INTEGER NOT NULL,
                    log_path TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    finished_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_authoring_runs_catalog
                ON authoring_runs(catalog_source_sha256);
                """
            )
            self._ensure_item_projection_columns()
            self._ensure_progress_columns()
            self.conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_authoring_items_catalog_scope
                ON authoring_items(status, exam, subject, chapter_id, topic_id);

                CREATE INDEX IF NOT EXISTS idx_authoring_items_parent_status
                ON authoring_items(parent_spec_id, status);
                """
            )
            self.conn.commit()

    def _ensure_progress_columns(self) -> None:
        """Add durable run/item progress fields to ledgers from older releases."""
        tables = {
            "authoring_runs": {
                "current_stage": "TEXT",
                "stage_updated_at": "TEXT",
            },
            "authoring_items": {
                "current_stage": "TEXT",
                "stage_updated_at": "TEXT",
            },
        }
        for table, columns in tables.items():
            existing = {
                row["name"]
                for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for name, declaration in columns.items():
                if name not in existing:
                    self.conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"
                    )

    def reserve_dispatch(
        self,
        run_id: str,
        dispatch_token: str,
        *,
        resume: bool,
        stale_after_seconds: int = 60,
    ) -> bool:
        """Atomically reserve one local worker launch for a durable run."""
        now = _now()
        cutoff = _timestamp(now - timedelta(seconds=max(1, stale_after_seconds)))
        now_text = _timestamp(now)
        with self._transaction() as conn:
            run = conn.execute(
                """
                SELECT status, lease_owner, lease_expires_at
                FROM authoring_runs WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if not run:
                raise KeyError(f"unknown authoring run: {run_id}")
            if run["status"] in {RunStatus.COMPLETED.value, RunStatus.CANCEL_REQUESTED.value}:
                raise ValueError(
                    f"authoring run {run_id} cannot dispatch from status {run['status']}"
                )

            existing = conn.execute(
                "SELECT * FROM authoring_dispatches WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if _dispatch_is_active(
                run,
                existing,
                now_text=now_text,
                cutoff=cutoff,
            ):
                return False

            conn.execute(
                """
                INSERT INTO authoring_dispatches (
                    run_id, dispatch_token, status, resume,
                    created_at, updated_at
                ) VALUES (?, ?, 'launching', ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    dispatch_token = excluded.dispatch_token,
                    status = 'launching',
                    pid = NULL,
                    resume = excluded.resume,
                    log_path = NULL,
                    error_message = NULL,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    finished_at = NULL
                """,
                (run_id, dispatch_token, int(resume), now_text, now_text),
            )
            conn.execute(
                """
                UPDATE authoring_runs
                SET current_stage = 'launching_worker', stage_updated_at = ?,
                    updated_at = ?
                WHERE run_id = ?
                """,
                (now_text, now_text, run_id),
            )
            return True

    def mark_dispatch_started(
        self,
        run_id: str,
        dispatch_token: str,
        *,
        pid: int,
        log_path: str,
    ) -> bool:
        with self._transaction() as conn:
            result = conn.execute(
                """
                UPDATE authoring_dispatches
                SET status = 'started', pid = ?, log_path = ?, updated_at = ?
                WHERE run_id = ? AND dispatch_token = ? AND status = 'launching'
                """,
                (pid, log_path, _timestamp(), run_id, dispatch_token),
            )
            return result.rowcount == 1

    def finish_dispatch(
        self,
        run_id: str,
        dispatch_token: str,
        *,
        status: str,
        error_message: str | None = None,
    ) -> bool:
        if status not in {"finished", "failed"}:
            raise ValueError("dispatch status must be finished or failed")
        now = _timestamp()
        with self._transaction() as conn:
            result = conn.execute(
                """
                UPDATE authoring_dispatches
                SET status = ?, error_message = ?, updated_at = ?, finished_at = ?
                WHERE run_id = ? AND dispatch_token = ?
                """,
                (status, error_message, now, now, run_id, dispatch_token),
            )
            if result.rowcount and status == "failed":
                conn.execute(
                    """
                    UPDATE authoring_runs
                    SET current_stage = 'worker_failed', stage_updated_at = ?,
                        updated_at = ?
                    WHERE run_id = ? AND status NOT IN (?, ?)
                    """,
                    (
                        now,
                        now,
                        run_id,
                        RunStatus.COMPLETED.value,
                        RunStatus.CANCELLED.value,
                    ),
                )
            return result.rowcount == 1

    def get_dispatch(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM authoring_dispatches WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return dict(row) if row else None

    def has_active_dispatch(
        self,
        run_id: str,
        *,
        stale_after_seconds: int = 60,
    ) -> bool:
        """Return whether a recent launch, live process, or run lease blocks execution."""
        now = _now()
        now_text = _timestamp(now)
        cutoff = _timestamp(now - timedelta(seconds=max(1, stale_after_seconds)))
        with self._lock:
            run = self.conn.execute(
                """
                SELECT lease_owner, lease_expires_at
                FROM authoring_runs WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if not run:
                raise KeyError(f"unknown authoring run: {run_id}")
            dispatch = self.conn.execute(
                "SELECT * FROM authoring_dispatches WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return _dispatch_is_active(
            run,
            dispatch,
            now_text=now_text,
            cutoff=cutoff,
        )

    def _ensure_item_projection_columns(self) -> None:
        """Migrate older ledgers and backfill query-efficient typed projections."""
        existing = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(authoring_items)").fetchall()
        }
        columns = {
            "exam": "TEXT",
            "subject": "TEXT",
            "chapter_id": "TEXT",
            "topic_id": "TEXT",
            "question_type": "TEXT",
            "parent_spec_id": "TEXT",
            "problem_latex": "TEXT",
            "projection_version": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, declaration in columns.items():
            if name not in existing:
                self.conn.execute(
                    f"ALTER TABLE authoring_items ADD COLUMN {name} {declaration}"
                )

        while True:
            rows = self.conn.execute(
                """
                SELECT spec_id, spec_json, last_candidate_json
                FROM authoring_items
                WHERE projection_version < 1
                LIMIT 500
                """
            ).fetchall()
            if not rows:
                break
            projections = []
            for row in rows:
                spec = GenerationSpec.model_validate_json(row["spec_json"])
                problem_latex = None
                if row["last_candidate_json"]:
                    candidate = AuthoredCandidate.model_validate_json(
                        row["last_candidate_json"]
                    )
                    problem_latex = candidate.problem_latex or None
                projections.append(
                    (
                        spec.exam,
                        spec.subject,
                        spec.chapter_id,
                        spec.topic_id,
                        spec.question_type.value,
                        spec.parent_spec_id,
                        problem_latex,
                        row["spec_id"],
                    )
                )
            self.conn.executemany(
                """
                UPDATE authoring_items
                SET exam = ?, subject = ?, chapter_id = ?, topic_id = ?,
                    question_type = ?, parent_spec_id = ?, problem_latex = ?,
                    projection_version = 1
                WHERE spec_id = ?
                """,
                projections,
            )

    def create_run(
        self,
        plan: AuthoringPlan,
        output_dir: str | Path,
        *,
        max_attempts: int = 3,
        concurrency: int = 2,
    ) -> str:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if concurrency < 1 or concurrency > 32:
            raise ValueError("concurrency must be between 1 and 32")
        resolved_output = Path(output_dir).expanduser().resolve()
        plan_json = _compact_plan_json(plan)
        plan_sha256 = _plan_sha256(plan)
        now = _timestamp()

        with self._transaction() as conn:
            existing = conn.execute(
                "SELECT plan_sha256, plan_json, output_dir FROM authoring_runs WHERE run_id = ?",
                (plan.plan_id,),
            ).fetchone()
            if existing:
                legacy_plan = "items" in json.loads(existing["plan_json"])
                matching_legacy_digest = (
                    legacy_plan
                    and existing["plan_sha256"] == _legacy_plan_sha256(plan)
                )
                if existing["plan_sha256"] != plan_sha256 and not matching_legacy_digest:
                    raise ValueError(f"run {plan.plan_id} exists with a different plan")
                if Path(existing["output_dir"]).resolve() != resolved_output:
                    raise ValueError(f"run {plan.plan_id} exists with a different output directory")
                return plan.plan_id

            self._validate_variant_plan_conn(conn, plan)
            self._validate_completion_plan_conn(conn, plan)

            conn.execute(
                """
                INSERT INTO authoring_runs (
                    run_id, status, request_json, plan_json, plan_sha256,
                    catalog_version, catalog_source_sha256, output_dir,
                    max_attempts, concurrency, current_stage, stage_updated_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    RunStatus.PENDING.value,
                    json.dumps(plan.request.model_dump(mode="json"), sort_keys=True),
                    plan_json,
                    plan_sha256,
                    plan.catalog_version,
                    plan.catalog_source_sha256,
                    str(resolved_output),
                    max_attempts,
                    concurrency,
                    "awaiting_start",
                    now,
                    now,
                    now,
                ),
            )
            conn.executemany(
                """
                INSERT INTO authoring_items (
                    spec_id, run_id, ordinal, status, spec_json,
                    exam, subject, chapter_id, topic_id, question_type,
                    parent_spec_id, projection_version, max_attempts,
                    next_attempt_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    (
                        spec.spec_id,
                        plan.plan_id,
                        spec.ordinal,
                        ItemStatus.PENDING.value,
                        json.dumps(spec.model_dump(mode="json"), sort_keys=True),
                        spec.exam,
                        spec.subject,
                        spec.chapter_id,
                        spec.topic_id,
                        spec.question_type.value,
                        spec.parent_spec_id,
                        max_attempts,
                        now,
                        now,
                        now,
                    )
                    for spec in plan.items
                ),
            )
        resolved_output.mkdir(parents=True, exist_ok=True)
        self.write_run_manifest(plan.plan_id)
        return plan.plan_id

    @staticmethod
    def _validate_completion_plan_conn(conn: sqlite3.Connection, plan: AuthoringPlan) -> None:
        completed = [spec for spec in plan.items if spec.source_kind.value == "completion"]
        if not completed and not plan.request.completion_parent_spec_ids:
            return
        if len(completed) != len(plan.items) or [spec.parent_spec_id for spec in completed] != plan.request.completion_parent_spec_ids:
            raise ValueError("completion plan has mismatched source items")
        for spec in completed:
            row = conn.execute("SELECT * FROM authoring_items WHERE spec_id = ?", (spec.parent_spec_id,)).fetchone()
            if not row or row["status"] not in {"accepted", "draft"}:
                raise ValueError("completion source must be an accepted problem or requested draft")
            parent = GenerationSpec.model_validate_json(row["spec_json"])
            candidate = AuthoredCandidate.model_validate_json(row["last_candidate_json"])
            if spec.parent_problem_latex != candidate.published_problem_latex:
                raise ValueError("completion must preserve the original question")
            if spec.parent_artifact_sha256 != hashlib.sha256(candidate.final_latex.encode()).hexdigest():
                raise ValueError("completion source changed after planning")
            if spec.parent_idea_latex != candidate.idea_latex or spec.parent_solution_latex != candidate.published_solution_latex or spec.parent_final_latex != candidate.final_latex:
                raise ValueError("completion must preserve the original components")
            if (candidate.idea_latex and not spec.include_idea) or (candidate.published_solution_latex and not spec.include_solution):
                raise ValueError("completion cannot remove existing components")
            if spec.parent_was_accepted != (row["status"] == "accepted"):
                raise ValueError("completion source validation status is incorrect")
            mutable_fields = {
                "spec_id", "ordinal", "source_kind", "variant_family", "parent_spec_id",
                "parent_problem_latex", "parent_artifact_sha256", "parent_idea_latex",
                "parent_solution_latex", "parent_final_latex", "parent_was_accepted",
                "include_solution", "include_idea",
            }
            for field in GenerationSpec.model_fields.keys() - mutable_fields:
                if getattr(spec, field) != getattr(parent, field):
                    raise ValueError(f"completion must preserve source {field}")

    @staticmethod
    def _validate_variant_plan_conn(conn: sqlite3.Connection, plan: AuthoringPlan) -> None:
        """Enforce accepted-parent lineage constraints under the create-run lock."""
        parent_id = plan.request.variant_parent_spec_id
        if not parent_id:
            return
        parent = conn.execute(
            "SELECT * FROM authoring_items WHERE spec_id = ?",
            (parent_id,),
        ).fetchone()
        if not parent or parent["status"] != ItemStatus.ACCEPTED.value:
            raise ValueError(
                f"variant parent {parent_id} must be an accepted item in this authoring database"
            )
        if not parent["last_candidate_json"]:
            raise ValueError(f"accepted variant parent {parent_id} has no candidate artifact")
        parent_spec = GenerationSpec.model_validate_json(parent["spec_json"])
        parent_candidate = AuthoredCandidate.model_validate_json(parent["last_candidate_json"])
        expected_root = parent_spec.lineage_root_spec_id or parent_spec.spec_id
        expected_depth = parent_spec.lineage_depth + 1
        parent_latex = parent_candidate.final_latex
        parent_digest = hashlib.sha256(parent_latex.encode()).hexdigest()
        if plan.request.variant_parent_artifact_sha256 != parent_digest:
            raise ValueError("variant parent artifact changed after the request was planned")

        for spec in plan.items:
            if spec.parent_spec_id != parent_id:
                raise ValueError("variant plan contains a mismatched parent_spec_id")
            if spec.lineage_root_spec_id != expected_root or spec.lineage_depth != expected_depth:
                raise ValueError("variant plan contains invalid lineage metadata")
            if spec.parent_artifact_sha256 != parent_digest or spec.parent_problem_latex != parent_latex:
                raise ValueError("variant plan is not bound to the accepted parent artifact")
            if (
                spec.exam != parent_spec.exam
                or spec.subject != parent_spec.subject
                or spec.chapter_id != parent_spec.chapter_id
                or spec.topic_id != parent_spec.topic_id
                or spec.question_type != parent_spec.question_type
            ):
                raise ValueError("variant plan must retain the accepted parent's exact syllabus/type identity")

        active_statuses = (
            ItemStatus.PENDING.value,
            ItemStatus.LEASED.value,
            ItemStatus.ACCEPTED.value,
            ItemStatus.NEEDS_REVIEW.value,
        )
        existing_children = int(
            conn.execute(
                """
                SELECT COUNT(*) AS count FROM authoring_items
                WHERE parent_spec_id = ? AND status IN (?, ?, ?, ?)
                """,
                (parent_id, *active_statuses),
            ).fetchone()["count"]
        )
        requested_total = existing_children + len(plan.items)
        if requested_total > plan.request.max_variants_per_parent:
            raise ValueError(
                f"variant parent {parent_id} would have {requested_total} active descendants; "
                f"cap is {plan.request.max_variants_per_parent}"
            )

    def acquire_run_lease(self, run_id: str, owner: str, lease_seconds: int = 300) -> bool:
        now = _now()
        expires = _timestamp(now + timedelta(seconds=lease_seconds))
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT status, lease_owner, lease_expires_at FROM authoring_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if not row:
                raise KeyError(f"unknown authoring run: {run_id}")
            if row["status"] in {RunStatus.COMPLETED.value, RunStatus.CANCELLED.value}:
                return False
            active_other = (
                row["lease_owner"]
                and row["lease_owner"] != owner
                and row["lease_expires_at"]
                and row["lease_expires_at"] > _timestamp(now)
            )
            if active_other:
                return False
            conn.execute(
                """
                UPDATE authoring_runs
                SET status = ?, current_stage = ?, stage_updated_at = ?,
                    lease_owner = ?, lease_expires_at = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (
                    RunStatus.RUNNING.value,
                    "preparing_run",
                    _timestamp(now),
                    owner,
                    expires,
                    _timestamp(now),
                    run_id,
                ),
            )
            return True

    def renew_run_lease(self, run_id: str, owner: str, lease_seconds: int = 300) -> bool:
        with self._transaction() as conn:
            result = conn.execute(
                """
                UPDATE authoring_runs SET lease_expires_at = ?, updated_at = ?
                WHERE run_id = ? AND lease_owner = ? AND status = ?
                """,
                (
                    _timestamp(_now() + timedelta(seconds=lease_seconds)),
                    _timestamp(),
                    run_id,
                    owner,
                    RunStatus.RUNNING.value,
                ),
            )
            return result.rowcount == 1

    def release_run_lease(self, run_id: str, owner: str) -> None:
        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE authoring_runs SET lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE run_id = ? AND lease_owner = ?
                """,
                (_timestamp(), run_id, owner),
            )

    def renew_item_lease(
        self,
        spec_id: str,
        owner: str,
        attempt: int,
        *,
        lease_seconds: int = 1800,
    ) -> bool:
        """Extend one in-flight attempt only while the caller still owns it."""
        with self._transaction() as conn:
            result = conn.execute(
                """
                UPDATE authoring_items SET lease_expires_at = ?, updated_at = ?
                WHERE spec_id = ? AND status = ? AND lease_owner = ? AND attempts = ?
                """,
                (
                    _timestamp(_now() + timedelta(seconds=lease_seconds)),
                    _timestamp(),
                    spec_id,
                    ItemStatus.LEASED.value,
                    owner,
                    attempt,
                ),
            )
            return result.rowcount == 1

    def set_run_stage(self, run_id: str, owner: str | None, stage: str) -> bool:
        """Persist a leased stage, or an idle rebuild's stage when no owner exists."""
        stage = _validate_stage(stage)
        now = _timestamp()
        with self._transaction() as conn:
            result = conn.execute(
                """
                UPDATE authoring_runs
                SET current_stage = ?, stage_updated_at = ?, updated_at = ?
                WHERE run_id = ? AND lease_owner IS ?
                """,
                (stage, now, now, run_id, owner),
            )
            return result.rowcount == 1

    def set_item_stage(self, claimed: ClaimedItem, stage: str) -> bool:
        """Persist the current stage only for the live, owner-bound attempt."""
        stage = _validate_stage(stage)
        now = _timestamp()
        with self._transaction() as conn:
            result = conn.execute(
                """
                UPDATE authoring_items
                SET current_stage = ?, stage_updated_at = ?, updated_at = ?
                WHERE spec_id = ? AND run_id = ? AND status = ?
                  AND lease_owner = ? AND attempts = ?
                """,
                (
                    stage,
                    now,
                    now,
                    claimed.spec.spec_id,
                    claimed.run_id,
                    ItemStatus.LEASED.value,
                    claimed.lease_owner,
                    claimed.attempt,
                ),
            )
            if result.rowcount:
                conn.execute(
                    """
                    UPDATE authoring_runs
                    SET current_stage = ?, stage_updated_at = ?, updated_at = ?
                    WHERE run_id = ?
                    """,
                    (stage, now, now, claimed.run_id),
                )
            return result.rowcount == 1

    def claim_next(
        self,
        run_id: str,
        worker_id: str,
        *,
        lease_seconds: int = 1800,
    ) -> ClaimedItem | None:
        now = _now()
        now_text = _timestamp(now)
        with self._transaction() as conn:
            run = conn.execute(
                "SELECT status, output_dir FROM authoring_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if not run:
                raise KeyError(f"unknown authoring run: {run_id}")
            if run["status"] in {
                RunStatus.CANCEL_REQUESTED.value,
                RunStatus.CANCELLED.value,
                RunStatus.COMPLETED.value,
            }:
                return None

            conn.execute(
                """
                UPDATE authoring_items
                SET status = ?, lease_owner = NULL, lease_expires_at = NULL,
                    current_stage = NULL, stage_updated_at = ?,
                    error_stage = 'worker_lease',
                    error_message = 'worker lease expired after final allowed attempt',
                    completed_at = ?, updated_at = ?
                WHERE run_id = ? AND status = ? AND lease_expires_at < ?
                  AND attempts >= max_attempts
                """,
                (
                    ItemStatus.FAILED.value,
                    now_text,
                    now_text,
                    now_text,
                    run_id,
                    ItemStatus.LEASED.value,
                    now_text,
                ),
            )
            conn.execute(
                """
                UPDATE authoring_items
                SET status = ?, lease_owner = NULL, lease_expires_at = NULL,
                    current_stage = NULL, stage_updated_at = ?,
                    retry_reason = COALESCE(retry_reason, 'worker lease expired'),
                    next_attempt_at = ?, updated_at = ?
                  WHERE run_id = ? AND status = ? AND lease_expires_at < ?
                    AND attempts < max_attempts
                """,
                (
                    ItemStatus.PENDING.value,
                    now_text,
                    now_text,
                    now_text,
                    run_id,
                    ItemStatus.LEASED.value,
                    now_text,
                ),
            )
            row = conn.execute(
                """
                SELECT * FROM authoring_items
                WHERE run_id = ? AND status = ? AND attempts < max_attempts
                  AND next_attempt_at <= ?
                ORDER BY ordinal
                LIMIT 1
                """,
                (run_id, ItemStatus.PENDING.value, now_text),
            ).fetchone()
            if not row:
                return None
            attempt = int(row["attempts"]) + 1
            conn.execute(
                """
                UPDATE authoring_items
                SET status = ?, attempts = ?, lease_owner = ?, lease_expires_at = ?,
                    current_stage = 'preparing_item', stage_updated_at = ?,
                    updated_at = ?, retry_reason = NULL
                WHERE spec_id = ?
                """,
                (
                    ItemStatus.LEASED.value,
                    attempt,
                    worker_id,
                    _timestamp(now + timedelta(seconds=lease_seconds)),
                    now_text,
                    now_text,
                    row["spec_id"],
                ),
            )
            conn.execute(
                """
                UPDATE authoring_runs
                SET current_stage = 'preparing_item', stage_updated_at = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (now_text, now_text, run_id),
            )
            spec = GenerationSpec.model_validate_json(row["spec_json"])
            item_dir = self.item_output_dir(Path(run["output_dir"]), run_id, spec)
            return ClaimedItem(
                run_id=run_id,
                spec=spec,
                attempt=attempt,
                max_attempts=int(row["max_attempts"]),
                output_dir=item_dir,
                lease_owner=worker_id,
                retry_reason=row["retry_reason"],
            )

    def record_candidate(
        self,
        claimed: ClaimedItem,
        candidate: AuthoredCandidate,
        *,
        artifact_dir: str | Path,
        artifact_sha256: str,
        retry_base_seconds: float = 2.0,
    ) -> ItemStatus:
        self._validate_candidate_record(
            claimed,
            candidate,
            artifact_dir=artifact_dir,
            artifact_sha256=artifact_sha256,
        )
        now = _now()
        candidate_json = json.dumps(candidate.model_dump(mode="json"), sort_keys=True)
        failure_reason = self._failure_reason(candidate)
        promoted_paths: list[Path] = []
        try:
            with self._transaction() as conn:
                row = conn.execute(
                    """
                    SELECT status, attempts, max_attempts, lease_owner, lease_expires_at
                    FROM authoring_items WHERE spec_id = ?
                    """,
                    (claimed.spec.spec_id,),
                ).fetchone()
                if not row:
                    raise KeyError(f"unknown authoring item: {claimed.spec.spec_id}")
                if row["status"] != ItemStatus.LEASED.value:
                    raise RuntimeError(f"item {claimed.spec.spec_id} is not leased")
                if int(row["attempts"]) != claimed.attempt:
                    raise RuntimeError(f"stale attempt for item {claimed.spec.spec_id}")
                if row["lease_owner"] != claimed.lease_owner:
                    raise RuntimeError(f"item lease ownership changed for {claimed.spec.spec_id}")
                if not row["lease_expires_at"] or row["lease_expires_at"] <= _timestamp(now):
                    raise RuntimeError(f"item lease expired for {claimed.spec.spec_id}")

                if candidate.status in {
                    CandidateStatus.ACCEPTED,
                    CandidateStatus.DRAFT,
                    CandidateStatus.NEEDS_REVIEW,
                }:
                    promoted_paths = self._promote_candidate_artifacts(claimed, candidate)

                conn.execute(
                    """
                    INSERT INTO authoring_attempts (
                        run_id, spec_id, attempt, candidate_status, candidate_json,
                        artifact_dir, artifact_sha256, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        claimed.run_id,
                        claimed.spec.spec_id,
                        claimed.attempt,
                        candidate.status.value,
                        candidate_json,
                        str(Path(artifact_dir).resolve()),
                        artifact_sha256,
                        _timestamp(now),
                    ),
                )
                conn.executemany(
                    """
                    INSERT INTO authoring_gates (
                        run_id, spec_id, attempt, gate_order, gate, required,
                        passed, summary, data_json, duration_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            claimed.run_id,
                            claimed.spec.spec_id,
                            claimed.attempt,
                            gate_index,
                            gate.gate,
                            int(gate.required),
                            int(gate.passed),
                            gate.summary,
                            json.dumps(gate.data, sort_keys=True),
                            gate.duration_ms,
                        )
                        for gate_index, gate in enumerate(candidate.gates, 1)
                    ],
                )

                run_status = conn.execute(
                    "SELECT status FROM authoring_runs WHERE run_id = ?",
                    (claimed.run_id,),
                ).fetchone()["status"]
                retry_allowed = (
                    candidate.status in {CandidateStatus.REJECTED, CandidateStatus.FAILED}
                    and claimed.attempt < claimed.max_attempts
                    and run_status != RunStatus.CANCEL_REQUESTED.value
                )
                if retry_allowed:
                    item_status = ItemStatus.PENDING
                    delay = retry_base_seconds * (2 ** max(0, claimed.attempt - 1))
                    next_attempt = _timestamp(now + timedelta(seconds=delay))
                    completed_at = None
                else:
                    item_status = ItemStatus(candidate.status.value)
                    if candidate.status in {CandidateStatus.REJECTED, CandidateStatus.FAILED} and candidate.problem_latex:
                        item_status = ItemStatus.NEEDS_REVIEW
                    next_attempt = _timestamp(now)
                    completed_at = _timestamp(now)

                conn.execute(
                    """
                    UPDATE authoring_items
                    SET status = ?, next_attempt_at = ?, lease_owner = NULL,
                        lease_expires_at = NULL, last_candidate_json = ?,
                        current_stage = NULL, stage_updated_at = ?,
                        problem_latex = ?,
                        error_stage = ?, error_message = ?, retry_reason = ?,
                        artifact_dir = ?, artifact_sha256 = ?, updated_at = ?,
                        completed_at = ?
                    WHERE spec_id = ?
                    """,
                    (
                        item_status.value,
                        next_attempt,
                        candidate_json,
                        _timestamp(now),
                        candidate.problem_latex or None,
                        candidate.error_stage,
                        candidate.error_message,
                        failure_reason if retry_allowed else None,
                        str(Path(artifact_dir).resolve()),
                        artifact_sha256,
                        _timestamp(now),
                        completed_at,
                        claimed.spec.spec_id,
                    ),
                )
                if item_status is ItemStatus.NEEDS_REVIEW and candidate.status is not CandidateStatus.NEEDS_REVIEW:
                    conn.execute(
                        "UPDATE authoring_items SET human_review_reason = ? WHERE spec_id = ?",
                        ("Automatic checks exhausted; awaiting the author's decision. " + failure_reason, claimed.spec.spec_id),
                    )
        except Exception:
            for path in reversed(promoted_paths):
                path.unlink(missing_ok=True)
            raise
        if item_status in {ItemStatus.ACCEPTED, ItemStatus.DRAFT, ItemStatus.NEEDS_REVIEW}:
            self.export_item_copy(claimed.run_id, claimed.spec.spec_id)
        run_status = self.refresh_run_status(claimed.run_id)
        if run_status in {RunStatus.COMPLETED, RunStatus.CANCELLED}:
            self.write_run_manifest(claimed.run_id)
        return item_status

    @staticmethod
    def _validate_candidate_record(
        claimed: ClaimedItem,
        candidate: AuthoredCandidate,
        *,
        artifact_dir: str | Path,
        artifact_sha256: str,
    ) -> None:
        """Reject stale, forged, or incomplete evidence before ledger mutation."""
        if candidate.spec != claimed.spec:
            raise ValueError("candidate specification does not match the claimed item")
        is_completion = claimed.spec.source_kind.value == "completion"
        if is_completion:
            if candidate.problem_latex and candidate.problem_latex != claimed.spec.parent_problem_latex:
                raise ValueError("component completion cannot change the original question")
            if candidate.status in {CandidateStatus.ACCEPTED, CandidateStatus.DRAFT, CandidateStatus.NEEDS_REVIEW}:
                preserved = [claimed.spec.parent_problem_latex, claimed.spec.parent_idea_latex, claimed.spec.parent_solution_latex]
                if claimed.spec.parent_solution_latex:
                    preserved.append(claimed.spec.parent_final_latex)
                if any(part and part not in candidate.final_latex for part in preserved):
                    raise ValueError("component completion must retain all original components")
        expected_dir = (
            claimed.output_dir / "attempts" / f"attempt-{claimed.attempt:03d}"
        ).resolve()
        actual_dir = Path(artifact_dir).expanduser().resolve()
        if actual_dir != expected_dir:
            raise ValueError("candidate artifact directory does not match the claimed attempt")
        candidate_path = actual_dir / "candidate.json"
        if not candidate_path.is_file():
            raise ValueError("candidate attempt artifact is missing candidate.json")
        persisted = AuthoredCandidate.model_validate_json(
            candidate_path.read_text(encoding="utf-8")
        )
        if persisted != candidate:
            raise ValueError("candidate evidence does not match its persisted attempt artifact")
        expected_sha256 = hashlib.sha256(
            _candidate_artifact_content(candidate).encode()
        ).hexdigest()
        if artifact_sha256 != expected_sha256:
            raise ValueError("candidate artifact SHA-256 does not match its content")

        if candidate.status is CandidateStatus.DRAFT:
            expected = ["draft", "structure"]
            if (claimed.spec.diagram_policy.value == "required" and not is_completion) or candidate.diagram_code:
                expected.append("problem_diagram")
            expected.extend(["final_structure", "compile"])
            if claimed.spec.include_solution or not candidate.final_latex:
                raise ValueError("draft delivery is only valid when solutions were explicitly deferred")
            if [gate.gate for gate in candidate.gates] != expected or any(not gate.passed or not gate.required for gate in candidate.gates):
                raise ValueError("draft delivery has incomplete structure/compile evidence")
            issues = validate_final_structure(claimed.spec, candidate.final_latex)
            if issues or candidate.error_stage or candidate.error_message:
                raise ValueError("draft delivery failed deterministic validation")
            return

        if candidate.status not in {
            CandidateStatus.ACCEPTED,
            CandidateStatus.NEEDS_REVIEW,
        }:
            return
        expects_review = claimed.spec.acceptance.human_review_required
        expected_status = (
            CandidateStatus.NEEDS_REVIEW
            if expects_review
            else CandidateStatus.ACCEPTED
        )
        if candidate.status is not expected_status:
            raise ValueError(
                f"passing candidate status must be {expected_status.value} for this review policy"
            )
        if not candidate.problem_latex or not candidate.final_latex:
            raise ValueError("passing candidate must contain problem and final LaTeX")
        if candidate.error_stage or candidate.error_message:
            raise ValueError("passing candidate cannot contain an error")
        structure_issues = validate_final_structure(
            claimed.spec,
            candidate.final_latex,
        )
        if structure_issues:
            raise ValueError(
                "passing candidate failed deterministic final validation: "
                + "; ".join(structure_issues)
            )

        expected_gates = list(REQUIRED_ACCEPTANCE_GATES)
        if claimed.spec.diagram_policy.value == "required" and not is_completion:
            expected_gates.insert(2, "problem_diagram")
        actual_gates = [gate.gate for gate in candidate.gates]
        failed = [
            gate.gate
            for gate in candidate.gates
            if not gate.required or not gate.passed
        ]
        if actual_gates != expected_gates or failed:
            details = [
                f"expected={','.join(expected_gates)}",
                f"actual={','.join(actual_gates)}",
            ]
            if failed:
                details.append(f"nonpassing={','.join(failed)}")
            raise ValueError(
                "passing candidate has incomplete acceptance evidence: "
                + "; ".join(details)
            )

    def abandon_item(self, claimed: ClaimedItem, reason: str) -> bool:
        """Release an infrastructure-failed claim only if it is still owned.

        The consumed attempt remains counted. A final allowed attempt becomes a
        terminal failure; otherwise the item is immediately retryable.
        """
        now = _timestamp()
        with self._transaction() as conn:
            row = conn.execute(
                """
                SELECT attempts, max_attempts FROM authoring_items
                WHERE spec_id = ? AND status = ? AND lease_owner = ? AND attempts = ?
                """,
                (
                    claimed.spec.spec_id,
                    ItemStatus.LEASED.value,
                    claimed.lease_owner,
                    claimed.attempt,
                ),
            ).fetchone()
            if not row:
                return False
            terminal = int(row["attempts"]) >= int(row["max_attempts"])
            status = ItemStatus.FAILED if terminal else ItemStatus.PENDING
            conn.execute(
                """
                UPDATE authoring_items
                SET status = ?, next_attempt_at = ?, lease_owner = NULL,
                    lease_expires_at = NULL, current_stage = NULL,
                    stage_updated_at = ?, error_stage = 'infrastructure',
                    error_message = ?, retry_reason = ?, updated_at = ?,
                    completed_at = ?
                WHERE spec_id = ?
                """,
                (
                    status.value,
                    now,
                    now,
                    reason,
                    None if terminal else reason,
                    now,
                    now if terminal else None,
                    claimed.spec.spec_id,
                ),
            )
            return True

    @staticmethod
    def _failure_reason(candidate: AuthoredCandidate) -> str:
        if candidate.error_message:
            return f"{candidate.error_stage}: {candidate.error_message}"
        failed = next((gate for gate in reversed(candidate.gates) if gate.required and not gate.passed), None)
        return f"{failed.gate}: {failed.summary}" if failed else candidate.status.value

    def request_cancel(self, run_id: str, reason: str = "user requested cancellation") -> None:
        now = _timestamp()
        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE authoring_runs
                SET status = ?, cancel_reason = ?, current_stage = ?,
                    stage_updated_at = ?, updated_at = ?
                WHERE run_id = ? AND status NOT IN (?, ?)
                """,
                (
                    RunStatus.CANCEL_REQUESTED.value,
                    reason,
                    "cancellation_requested",
                    now,
                    now,
                    run_id,
                    RunStatus.COMPLETED.value,
                    RunStatus.CANCELLED.value,
                ),
            )
            conn.execute(
                """
                UPDATE authoring_items
                SET status = ?, current_stage = NULL, stage_updated_at = ?,
                    completed_at = ?, updated_at = ?
                WHERE run_id = ? AND status = ?
                """,
                (
                    ItemStatus.CANCELLED.value,
                    now,
                    now,
                    now,
                    run_id,
                    ItemStatus.PENDING.value,
                ),
            )
        self.refresh_run_status(run_id)
        self.write_run_manifest(run_id)

    def resume_run(self, run_id: str) -> int:
        now = _timestamp()
        with self._transaction() as conn:
            run = conn.execute(
                """
                SELECT status, current_stage, stage_updated_at, completed_at
                FROM authoring_runs WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if not run:
                raise KeyError(f"unknown authoring run: {run_id}")
            reset = conn.execute(
                """
                UPDATE authoring_items
                SET status = ?, next_attempt_at = ?, completed_at = NULL,
                    lease_owner = NULL, lease_expires_at = NULL,
                    current_stage = NULL, stage_updated_at = ?, updated_at = ?
                WHERE run_id = ? AND status = ? AND attempts < max_attempts
                """,
                (
                    ItemStatus.PENDING.value,
                    now,
                    now,
                    now,
                    run_id,
                    ItemStatus.CANCELLED.value,
                ),
            ).rowcount
            conn.execute(
                """
                UPDATE authoring_runs
                SET status = ?, cancel_reason = NULL, completed_at = NULL,
                    current_stage = 'awaiting_start', stage_updated_at = ?,
                    lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE run_id = ?
                """,
                (RunStatus.PENDING.value, now, now, run_id),
            )
            return reset

    def review_item(self, run_id: str, spec_id: str, *, approve: bool, reason: str) -> None:
        """Record a human decision and promote the corresponding artifact atomically.

        Approval repeats the accepted-only novelty check because multiple candidates
        can wait for review concurrently.  Attempt records remain unchanged as the
        immutable machine-produced evidence; the reviewed state is stored on the item
        and in ``authoring_reviews``.
        """
        status = ItemStatus.ACCEPTED if approve else ItemStatus.REJECTED
        now = _timestamp()
        reason = reason.strip()
        if not reason:
            raise ValueError("a human review reason is required")

        review_path: Path | None = None
        published_path: Path | None = None
        published_created = False
        item_candidate_path: Path | None = None
        original_candidate_json: str | None = None
        try:
            with self._transaction() as conn:
                row = conn.execute(
                    """
                    SELECT i.*, r.output_dir, r.catalog_source_sha256
                    FROM authoring_items AS i
                    JOIN authoring_runs AS r ON r.run_id = i.run_id
                    WHERE i.run_id = ? AND i.spec_id = ?
                    """,
                    (run_id, spec_id),
                ).fetchone()
                if not row:
                    raise KeyError(f"unknown authoring item: {spec_id}")
                if row["status"] != ItemStatus.NEEDS_REVIEW.value:
                    raise ValueError(f"item {spec_id} is not awaiting human review")
                if not row["last_candidate_json"]:
                    raise ValueError(f"item {spec_id} has no reviewable candidate")

                spec = GenerationSpec.model_validate_json(row["spec_json"])
                candidate = AuthoredCandidate.model_validate_json(row["last_candidate_json"])
                if approve:
                    required = set(REQUIRED_ACCEPTANCE_GATES)
                    passing = {gate.gate for gate in candidate.gates if gate.passed and gate.required}
                    if not spec.include_solution or required - passing or any(gate.required and not gate.passed for gate in candidate.gates):
                        raise ValueError("this draft still has failed or missing checks; keep it for review or revise it before approval")
                    if validate_final_structure(spec, candidate.final_latex):
                        raise ValueError("this draft is structurally incomplete and cannot be approved")
                if approve and not (
                    spec.source_kind.value == "completion" and spec.parent_was_accepted
                ):
                    novelty = NoveltyIndex()
                    for accepted_id, problem_latex in self._accepted_documents_for_catalog_conn(
                        conn,
                        exam=spec.exam,
                        subject=spec.subject,
                        catalog_source_sha256=spec.syllabus_source_sha256,
                    ):
                        novelty.add(accepted_id, problem_latex)
                    if spec.source_kind.value == "variant":
                        check = novelty.check_variant(
                            candidate.problem_latex,
                            spec.acceptance.novelty_threshold,
                            parent_id=spec.parent_spec_id,
                            exact_only=(
                                spec.variant_family is not None
                                and spec.variant_family.value == "numerical"
                            ),
                        )
                    else:
                        check = novelty.check(
                            candidate.problem_latex,
                            spec.acceptance.novelty_threshold,
                        )
                    if not check.passed:
                        raise ValueError(
                            "review approval failed accepted-only novelty check: "
                            f"similarity {check.max_similarity:.3f} to {check.closest_id}"
                        )

                candidate.status = (
                    CandidateStatus.ACCEPTED if approve else CandidateStatus.REJECTED
                )
                candidate.completed_at = now
                candidate.review = {
                    **candidate.review,
                    "human_review": {
                        "decision": "approved" if approve else "rejected",
                        "reason": reason,
                        "reviewed_at": now,
                    },
                }
                reviewed_json = json.dumps(candidate.model_dump(mode="json"), sort_keys=True)

                item_dir = self.item_output_dir(Path(row["output_dir"]), run_id, spec)
                run_dir = item_dir.parent.parent
                filename = f"problem_{spec.ordinal:06d}_{spec.spec_id[:12]}.tex"
                collection = "accepted" if approve else "review_rejected"
                review_path = run_dir / collection / filename
                artifact_content = candidate.final_latex or candidate.problem_latex
                if not artifact_content:
                    raise ValueError(f"item {spec_id} has no reviewable LaTeX artifact")
                final_content = artifact_content.rstrip() + "\n"
                _atomic_write(review_path, final_content)
                if approve:
                    published_path = generated_artifact_path(
                        Path(row["output_dir"]),
                        run_id,
                        spec,
                    )
                    published_created = _write_immutable(
                        published_path,
                        final_content,
                    )
                item_candidate_path = item_dir / "candidate.json"
                original_candidate_json = row["last_candidate_json"]
                _atomic_write(item_candidate_path, json.dumps(candidate.model_dump(mode="json"), indent=2, sort_keys=True) + "\n")

                conn.execute(
                    """
                    UPDATE authoring_items SET status = ?, human_review_reason = ?,
                        last_candidate_json = ?, completed_at = ?, updated_at = ?
                    WHERE spec_id = ?
                    """,
                    (status.value, reason, reviewed_json, now, now, spec_id),
                )
                conn.execute(
                    """
                    INSERT INTO authoring_reviews (run_id, spec_id, decision, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (run_id, spec_id, "approved" if approve else "rejected", reason, now),
                )
        except Exception:
            if review_path is not None:
                review_path.unlink(missing_ok=True)
            if published_path is not None and published_created:
                published_path.unlink(missing_ok=True)
            if item_candidate_path is not None and original_candidate_json is not None:
                _atomic_write(
                    item_candidate_path,
                    json.dumps(json.loads(original_candidate_json), indent=2, sort_keys=True) + "\n",
                )
            raise

        spec = GenerationSpec.model_validate_json(self.get_item(spec_id)["spec_json"])
        pending_review_path = (
            self.item_output_dir(Path(self.get_run(run_id)["output_dir"]), run_id, spec).parent.parent
            / "needs_review"
            / f"problem_{spec.ordinal:06d}_{spec.spec_id[:12]}.tex"
        )
        pending_review_path.unlink(missing_ok=True)
        self.export_item_copy(run_id, spec_id)
        self.refresh_run_status(run_id)
        self.write_run_manifest(run_id)

    def export_item_copy(self, run_id: str, spec_id: str) -> None:
        """A filesystem conflict never erases an accepted or reviewable candidate."""
        from vbagent.authoring.exports import export_item

        try:
            export_item(self, run_id, spec_id)
        except Exception:
            logging.getLogger(__name__).warning("human export needs attention for %s", spec_id, exc_info=True)

    def restore_unreviewed_rejections(self, run_id: str) -> int:
        """Explicit rebuild migrates machine-only rejections to author review."""
        with self._transaction() as conn:
            rows = conn.execute(
                "SELECT i.spec_id, i.last_candidate_json FROM authoring_items AS i "
                "WHERE i.run_id = ? AND i.status = 'rejected' AND COALESCE(i.problem_latex, '') != '' "
                "AND NOT EXISTS (SELECT 1 FROM authoring_reviews AS r WHERE r.spec_id = i.spec_id AND r.decision = 'rejected')",
                (run_id,),
            ).fetchall()
            for row in rows:
                candidate = AuthoredCandidate.model_validate_json(row["last_candidate_json"])
                conn.execute("UPDATE authoring_items SET status = 'needs_review', human_review_reason = ?, updated_at = ? WHERE spec_id = ?", ("Awaiting author decision: " + self._failure_reason(candidate), _timestamp(), row["spec_id"]))
        return len(rows)

    def defer_or_revise_item(self, run_id: str, spec_id: str, *, reason: str, revise: bool) -> None:
        if not reason.strip():
            raise ValueError("an author decision needs a reason")
        with self._transaction() as conn:
            item = conn.execute("SELECT * FROM authoring_items WHERE run_id = ? AND spec_id = ?", (run_id, spec_id)).fetchone()
            if not item or item["status"] != ItemStatus.NEEDS_REVIEW.value:
                raise ValueError("only a draft awaiting author review can be kept or revised")
            now = _timestamp()
            conn.execute("INSERT INTO authoring_reviews (run_id, spec_id, decision, reason, created_at) VALUES (?, ?, ?, ?, ?)", (run_id, spec_id, "revise" if revise else "keep", reason.strip(), now))
            if revise:
                conn.execute("UPDATE authoring_items SET status = 'pending', max_attempts = attempts + 1, retry_reason = ?, next_attempt_at = ?, completed_at = NULL, human_review_reason = ?, updated_at = ? WHERE spec_id = ?", (reason.strip(), now, reason.strip(), now, spec_id))
                conn.execute("UPDATE authoring_runs SET status = 'pending', current_stage = 'awaiting_start', completed_at = NULL, updated_at = ? WHERE run_id = ?", (now, run_id))
            else:
                conn.execute("UPDATE authoring_items SET human_review_reason = ?, updated_at = ? WHERE spec_id = ?", ("Kept by author: " + reason.strip(), now, spec_id))
        if not revise:
            self.export_item_copy(run_id, spec_id)
        self.write_run_manifest(run_id)

    def refresh_run_status(self, run_id: str) -> RunStatus:
        with self._transaction() as conn:
            run = conn.execute(
                """
                SELECT status, current_stage, stage_updated_at, completed_at
                FROM authoring_runs WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if not run:
                raise KeyError(f"unknown authoring run: {run_id}")
            has_items = conn.execute(
                "SELECT 1 FROM authoring_items WHERE run_id = ? LIMIT 1",
                (run_id,),
            ).fetchone() is not None
            active = conn.execute(
                """
                SELECT 1 FROM authoring_items
                WHERE run_id = ? AND status IN (?, ?)
                LIMIT 1
                """,
                (run_id, ItemStatus.PENDING.value, ItemStatus.LEASED.value),
            ).fetchone() is not None
            if run["status"] == RunStatus.CANCEL_REQUESTED.value and not active:
                new_status = RunStatus.CANCELLED
            elif has_items and not active:
                new_status = RunStatus.COMPLETED
            else:
                new_status = RunStatus(run["status"])
            now = _timestamp()
            is_terminal = new_status in {RunStatus.COMPLETED, RunStatus.CANCELLED}
            completed_at = (run["completed_at"] or now) if is_terminal else None
            current_stage = run["current_stage"]
            stage_updated_at = run["stage_updated_at"]
            if new_status is RunStatus.CANCELLED:
                current_stage = "cancelled"
                stage_updated_at = now
            elif (
                new_status is RunStatus.COMPLETED
                and run["status"] != RunStatus.COMPLETED.value
            ):
                current_stage = "awaiting_final_assembly"
                stage_updated_at = now
            conn.execute(
                """
                UPDATE authoring_runs
                SET status = ?, current_stage = ?, stage_updated_at = ?,
                    completed_at = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (
                    new_status.value,
                    current_stage,
                    stage_updated_at,
                    completed_at,
                    now,
                    run_id,
                ),
            )
            return new_status

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM authoring_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"unknown authoring run: {run_id}")
        return dict(row)

    def load_plan(self, run_id: str) -> AuthoringPlan:
        """Load the immutable plan snapshot persisted for a run."""
        run = self.get_run(run_id)
        payload = json.loads(run["plan_json"])
        if "items" not in payload:
            with self._lock:
                rows = self.conn.execute(
                    """
                    SELECT spec_json FROM authoring_items
                    WHERE run_id = ? ORDER BY ordinal
                    """,
                    (run_id,),
                ).fetchall()
            payload["items"] = [json.loads(row["spec_json"]) for row in rows]
        return AuthoringPlan.model_validate(payload)

    def load_request(self, run_id: str) -> AuthoringRequest:
        """Load only the typed request without materializing every plan item."""
        return AuthoringRequest.model_validate_json(self.get_run(run_id)["request_json"])

    def run_scope(self, run_id: str) -> dict[str, Any]:
        """Return resolved chapter/topic labels without loading every item."""
        request = self.load_request(run_id)
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT spec_json, MIN(ordinal) AS first_ordinal
                FROM authoring_items
                WHERE run_id = ?
                GROUP BY chapter_id, topic_id
                ORDER BY first_ordinal
                """,
                (run_id,),
            ).fetchall()
        specs = [GenerationSpec.model_validate_json(row["spec_json"]) for row in rows]
        return {
            "exam": request.exam,
            "subject": request.subject,
            "chapter_ids": list(dict.fromkeys(spec.chapter_id for spec in specs)),
            "chapters": list(dict.fromkeys(spec.chapter for spec in specs)),
            "topic_ids": list(dict.fromkeys(spec.topic_id for spec in specs)),
            "topics": list(dict.fromkeys(spec.topic for spec in specs)),
        }

    def run_progress(self, run_id: str) -> dict[str, Any]:
        """Return durable run and active-item stages for live status clients."""
        with self._lock:
            run = self.conn.execute(
                """
                SELECT current_stage, stage_updated_at
                FROM authoring_runs WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if not run:
                raise KeyError(f"unknown authoring run: {run_id}")
            rows = self.conn.execute(
                """
                SELECT spec_id, ordinal, attempts, lease_owner, current_stage,
                       stage_updated_at, spec_json
                FROM authoring_items
                WHERE run_id = ? AND status = ?
                ORDER BY COALESCE(stage_updated_at, '') DESC, ordinal
                """,
                (run_id, ItemStatus.LEASED.value),
            ).fetchall()
            post_draft = ",".join("?" for _ in _POST_DRAFT_STAGES)
            counts_row = self.conn.execute(
                f"""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN COALESCE(problem_latex, '') != ''
                           OR current_stage IN ({post_draft})
                           OR EXISTS (
                               SELECT 1 FROM authoring_gates g
                               WHERE g.spec_id = i.spec_id AND g.gate = 'draft'
                                 AND g.passed = 1
                           ) THEN 1 ELSE 0 END) AS drafted,
                       SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS accepted,
                       SUM(CASE WHEN status = 'leased'
                           AND current_stage IN ({post_draft}) THEN 1 ELSE 0 END) AS checking,
                       SUM(CASE WHEN (status = 'pending' AND attempts > 0)
                           OR (status = 'leased' AND attempts > 1)
                           THEN 1 ELSE 0 END) AS retrying,
                       SUM(CASE WHEN attempts = 0 THEN 1 ELSE 0 END) AS not_started,
                       SUM(CASE WHEN status = 'needs_review' THEN 1 ELSE 0 END) AS needs_review,
                       SUM(CASE WHEN status IN ('rejected', 'failed')
                           THEN 1 ELSE 0 END) AS unsuccessful,
                       SUM(attempts) AS attempts
                FROM authoring_items i WHERE run_id = ?
                """,
                (*_POST_DRAFT_STAGES, *_POST_DRAFT_STAGES, run_id),
            ).fetchone()
            failure = self.conn.execute(
                """
                SELECT g.spec_id, i.ordinal, g.attempt, g.gate, g.summary
                FROM authoring_gates g JOIN authoring_items i ON i.spec_id = g.spec_id
                WHERE i.run_id = ? AND g.passed = 0
                ORDER BY g.id DESC LIMIT 1
                """,
                (run_id,),
            ).fetchone()

        active_stages: list[dict[str, Any]] = []
        stage_counts: dict[str, int] = {}
        for row in rows:
            spec = GenerationSpec.model_validate_json(row["spec_json"])
            stage = str(row["current_stage"] or "preparing_item")
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            active_stages.append(
                {
                    "spec_id": row["spec_id"],
                    "ordinal": int(row["ordinal"]),
                    "attempt": int(row["attempts"]),
                    "stage": stage,
                    "stage_updated_at": row["stage_updated_at"],
                    "worker_id": row["lease_owner"],
                    "chapter": spec.chapter,
                    "topic": spec.topic,
                }
            )

        current_stage = (
            active_stages[0]["stage"]
            if active_stages
            else run["current_stage"]
        )
        stage_updated_at = (
            active_stages[0]["stage_updated_at"]
            if active_stages
            else run["stage_updated_at"]
        )
        return {
            "current_stage": current_stage,
            "stage_updated_at": stage_updated_at,
            "active_stages": active_stages,
            "stage_counts": stage_counts,
            "progress_counts": {key: int(counts_row[key] or 0) for key in counts_row.keys()},
            "latest_failure": dict(failure) if failure is not None else None,
        }

    def plan_metadata(self, run_id: str) -> dict[str, Any]:
        """Return immutable plan-level metadata without the item array."""
        payload = json.loads(self.get_run(run_id)["plan_json"])
        payload.pop("items", None)
        return payload

    def get_item(self, spec_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM authoring_items WHERE spec_id = ?",
                (spec_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"unknown authoring item: {spec_id}")
        return dict(row)

    def get_run_item(self, run_id: str, spec_id: str) -> dict[str, Any]:
        """Load one item while enforcing its run boundary."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT * FROM authoring_items
                WHERE run_id = ? AND spec_id = ?
                """,
                (run_id, spec_id),
            ).fetchone()
        if not row:
            raise KeyError(f"unknown authoring item {spec_id} in run {run_id}")
        return dict(row)

    def list_items(self, run_id: str, status: ItemStatus | str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM authoring_items WHERE run_id = ?"
        params: list[Any] = [run_id]
        if status is not None:
            query += " AND status = ?"
            params.append(status.value if isinstance(status, ItemStatus) else status)
        query += " ORDER BY ordinal"
        with self._lock:
            rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def list_item_results(self, run_id: str) -> list[dict[str, Any]]:
        """Load caller-facing outcomes without duplicating immutable spec JSON."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT spec_id, run_id, ordinal, status, attempts,
                       last_candidate_json, error_stage, error_message,
                       artifact_dir, artifact_sha256, human_review_reason,
                       completed_at
                FROM authoring_items
                WHERE run_id = ?
                ORDER BY ordinal
                """,
                (run_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_item_results_page(
        self,
        run_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        status: ItemStatus | str | None = None,
        include_candidate: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        """Load a bounded result page suitable for interactive clients.

        Immutable specifications are decoded only for the selected page. Full
        candidate evidence remains opt-in so large runs cannot accidentally be
        materialized into one MCP or CLI response.
        """
        if offset < 0:
            raise ValueError("offset cannot be negative")
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        self.get_run(run_id)

        status_value: str | None = None
        if status is not None:
            try:
                status_value = (
                    status.value
                    if isinstance(status, ItemStatus)
                    else ItemStatus(status).value
                )
            except ValueError as exc:
                allowed = ", ".join(item.value for item in ItemStatus)
                raise ValueError(f"invalid item status; expected one of: {allowed}") from exc

        where = "run_id = ?"
        params: list[Any] = [run_id]
        if status_value is not None:
            where += " AND status = ?"
            params.append(status_value)

        candidate_column = ", last_candidate_json" if include_candidate else ""
        with self._lock:
            total = int(
                self.conn.execute(
                    f"SELECT COUNT(*) AS count FROM authoring_items WHERE {where}",
                    params,
                ).fetchone()["count"]
            )
            rows = self.conn.execute(
                f"""
                SELECT spec_id, run_id, ordinal, status, attempts, max_attempts,
                       spec_json, error_stage, error_message, artifact_sha256,
                       human_review_reason, completed_at{candidate_column}
                FROM authoring_items
                WHERE {where}
                ORDER BY ordinal
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            spec = GenerationSpec.model_validate_json(item.pop("spec_json"))
            item.update(
                {
                    "exam": spec.exam,
                    "subject": spec.subject,
                    "chapter_id": spec.chapter_id,
                    "chapter": spec.chapter,
                    "topic_id": spec.topic_id,
                    "topic": spec.topic,
                    "question_type": spec.question_type.value,
                    "difficulty": spec.difficulty,
                    "cognitive_level": spec.cognitive_level.value,
                    "representation": spec.representation.value,
                    "diagram_policy": spec.diagram_policy.value,
                    "source_kind": spec.source_kind.value,
                    "parent_spec_id": spec.parent_spec_id,
                }
            )
            if include_candidate and item.get("last_candidate_json"):
                item["candidate"] = json.loads(item.pop("last_candidate_json"))
            else:
                item.pop("last_candidate_json", None)
            results.append(item)
        return results, total

    def item_evidence(self, run_id: str, spec_id: str) -> dict[str, Any]:
        """Return the immutable spec, attempts, and ordered gate evidence."""
        item = self.get_run_item(run_id, spec_id)
        with self._lock:
            attempts = self.conn.execute(
                """
                SELECT attempt, candidate_status, candidate_json,
                       artifact_sha256, created_at
                FROM authoring_attempts
                WHERE run_id = ? AND spec_id = ?
                ORDER BY attempt
                """,
                (run_id, spec_id),
            ).fetchall()
            gates = self.conn.execute(
                """
                SELECT attempt, gate_order, gate, required, passed, summary,
                       data_json, duration_ms
                FROM authoring_gates
                WHERE run_id = ? AND spec_id = ?
                ORDER BY attempt, gate_order
                """,
                (run_id, spec_id),
            ).fetchall()

        gates_by_attempt: dict[int, list[dict[str, Any]]] = {}
        for row in gates:
            gate = dict(row)
            attempt_number = int(gate.pop("attempt"))
            gate["required"] = bool(gate["required"])
            gate["passed"] = bool(gate["passed"])
            gate["data"] = json.loads(gate.pop("data_json"))
            gates_by_attempt.setdefault(attempt_number, []).append(gate)

        attempt_records: list[dict[str, Any]] = []
        for row in attempts:
            record = dict(row)
            attempt_number = int(record["attempt"])
            record["candidate"] = json.loads(record.pop("candidate_json"))
            record["gates"] = gates_by_attempt.get(attempt_number, [])
            attempt_records.append(record)

        return {
            "run_id": run_id,
            "spec_id": spec_id,
            "status": item["status"],
            "attempts_used": int(item["attempts"]),
            "max_attempts": int(item["max_attempts"]),
            "spec": json.loads(item["spec_json"]),
            "attempts": attempt_records,
            "human_review_reason": item["human_review_reason"],
        }

    def stats(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            run = self.get_run(run_id)
            rows = self.conn.execute(
                """
                SELECT status, COUNT(*) AS count, SUM(attempts) AS attempts
                FROM authoring_items WHERE run_id = ? GROUP BY status
                """,
                (run_id,),
            ).fetchall()
        counts = {status.value: 0 for status in ItemStatus}
        attempts = 0
        for row in rows:
            counts[row["status"]] = int(row["count"])
            attempts += int(row["attempts"] or 0)
        return {
            "run_id": run_id,
            "status": run["status"],
            "total": sum(counts.values()),
            "attempts": attempts,
            **counts,
        }

    def accepted_coverage(self, run_id: str) -> dict[str, dict[str, int]]:
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT chapter_id, topic_id, COUNT(*) AS count
                FROM authoring_items
                WHERE run_id = ? AND status = ?
                GROUP BY chapter_id, topic_id
                """,
                (run_id, ItemStatus.ACCEPTED.value),
            ).fetchall()
        chapters: dict[str, int] = {}
        topics: dict[str, int] = {}
        for row in rows:
            count = int(row["count"])
            chapters[row["chapter_id"]] = chapters.get(row["chapter_id"], 0) + count
            topics[row["topic_id"]] = topics.get(row["topic_id"], 0) + count
        return {"chapter": dict(sorted(chapters.items())), "topic": dict(sorted(topics.items()))}

    def accepted_coverage_for_catalog(
        self,
        *,
        exam: str,
        subject: str,
        catalog_source_sha256: str,
    ) -> dict[str, dict[str, int]]:
        """Accepted coverage across every run sharing one exact catalog snapshot."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT i.chapter_id, i.topic_id, COUNT(*) AS count
                FROM authoring_items AS i
                JOIN authoring_runs AS r ON r.run_id = i.run_id
                WHERE i.status = ? AND r.catalog_source_sha256 = ?
                  AND i.exam = ? AND i.subject = ?
                  AND NOT EXISTS (
                    SELECT 1 FROM authoring_items AS child
                    WHERE child.parent_spec_id = i.spec_id AND child.status = 'accepted'
                      AND json_extract(child.spec_json, '$.source_kind') = 'completion'
                  )
                GROUP BY i.chapter_id, i.topic_id
                """,
                (ItemStatus.ACCEPTED.value, catalog_source_sha256, exam, subject),
            ).fetchall()
        chapters: dict[str, int] = {}
        topics: dict[str, int] = {}
        for row in rows:
            count = int(row["count"])
            chapters[row["chapter_id"]] = chapters.get(row["chapter_id"], 0) + count
            topics[row["topic_id"]] = topics.get(row["topic_id"], 0) + count
        return {"chapter": dict(sorted(chapters.items())), "topic": dict(sorted(topics.items()))}

    def accepted_documents(self, run_id: str) -> list[tuple[str, str]]:
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT spec_id, problem_latex FROM authoring_items
                WHERE run_id = ? AND status = ? AND problem_latex IS NOT NULL
                """,
                (run_id, ItemStatus.ACCEPTED.value),
            ).fetchall()
        return [(row["spec_id"], row["problem_latex"]) for row in rows]

    def accepted_documents_for_catalog(
        self,
        *,
        exam: str,
        subject: str,
        catalog_source_sha256: str,
    ) -> list[tuple[str, str]]:
        """Accepted problem documents across runs for novelty comparisons."""
        with self._lock:
            return self._accepted_documents_for_catalog_conn(
                self.conn,
                exam=exam,
                subject=subject,
                catalog_source_sha256=catalog_source_sha256,
            )

    @staticmethod
    def _accepted_documents_for_catalog_conn(
        conn: sqlite3.Connection,
        *,
        exam: str,
        subject: str,
        catalog_source_sha256: str,
    ) -> list[tuple[str, str]]:
        rows = conn.execute(
            """
            SELECT i.spec_id, i.problem_latex
            FROM authoring_items AS i
            JOIN authoring_runs AS r ON r.run_id = i.run_id
            WHERE i.status = ? AND i.problem_latex IS NOT NULL
              AND r.catalog_source_sha256 = ?
              AND i.exam = ? AND i.subject = ?
              AND NOT EXISTS (
                SELECT 1 FROM authoring_items AS child
                WHERE child.parent_spec_id = i.spec_id AND child.status = 'accepted'
                  AND json_extract(child.spec_json, '$.source_kind') = 'completion'
              )
            """,
            (ItemStatus.ACCEPTED.value, catalog_source_sha256, exam, subject),
        ).fetchall()
        return [(row["spec_id"], row["problem_latex"]) for row in rows]

    def usage_summary(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT candidate_json FROM authoring_attempts WHERE run_id = ?",
                (run_id,),
            ).fetchall()
        totals = {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "ordinary_input_tokens": 0,
            "cache_read_requests": 0,
            "cache_reported_requests": 0,
            "cache_metrics_reported_calls": 0,
            "cache_metrics_reported_input_tokens": 0,
            "effective_input_eligible_tokens": 0,
            "effective_input_cost_units": 0.0,
            "reasoning_tokens": 0,
            "duration_seconds": 0.0,
            "profile_failovers": 0,
        }
        profiles: dict[str, int] = {}
        cache_domains: dict[str, int] = {}
        profile_usage: dict[str, dict[str, Any]] = {}
        cache_domain_usage: dict[str, dict[str, Any]] = {}
        bucket_fields = (
            "requests",
            "input_tokens",
            "output_tokens",
            "cached_tokens",
            "cache_write_tokens",
            "ordinary_input_tokens",
            "cache_read_requests",
            "cache_reported_requests",
            "cache_metrics_reported_input_tokens",
            "effective_input_eligible_tokens",
            "effective_input_cost_units",
            "failovers",
        )

        def merge_buckets(
            target: dict[str, dict[str, Any]],
            source: dict[str, dict[str, Any]],
        ) -> None:
            for name, source_bucket in source.items():
                bucket = target.setdefault(
                    name,
                    {field: 0 for field in bucket_fields},
                )
                for field in bucket_fields:
                    bucket[field] += source_bucket.get(field, 0) or 0

        for row in rows:
            candidate = json.loads(row["candidate_json"])
            usage_record = candidate.get("provenance", {}).get("usage", {})
            usage = usage_record.get("totals", {})
            for key in totals:
                totals[key] += usage.get(key, 0) or 0
            for name, count in (usage_record.get("profiles") or {}).items():
                profiles[name] = profiles.get(name, 0) + int(count or 0)
            for domain, count in (usage_record.get("cache_domains") or {}).items():
                cache_domains[domain] = cache_domains.get(domain, 0) + int(count or 0)
            merge_buckets(profile_usage, usage_record.get("profile_usage") or {})
            merge_buckets(
                cache_domain_usage,
                usage_record.get("cache_domain_usage") or {},
            )
        totals["duration_seconds"] = round(float(totals["duration_seconds"]), 4)
        input_tokens = totals["input_tokens"]
        totals["cache_hit_percent"] = round(
            totals["cached_tokens"] / input_tokens * 100, 2
        ) if input_tokens else 0.0
        totals["cache_write_percent"] = round(
            totals["cache_write_tokens"] / input_tokens * 100, 2
        ) if input_tokens else 0.0
        reported_requests = totals["cache_reported_requests"]
        totals["cache_request_hit_percent"] = (
            round(totals["cache_read_requests"] / reported_requests * 100, 2)
            if reported_requests
            else None
        )
        totals["effective_input_multiplier"] = (
            round(totals["effective_input_cost_units"] / input_tokens, 4)
            if input_tokens
            and totals["effective_input_eligible_tokens"] == input_tokens
            else None
        )
        totals["profiles"] = profiles
        totals["cache_domains"] = cache_domains
        totals["profile_usage"] = {
            name: _finalize_usage_bucket(bucket)
            for name, bucket in profile_usage.items()
        }
        totals["cache_domain_usage"] = {
            name: _finalize_usage_bucket(bucket)
            for name, bucket in cache_domain_usage.items()
        }
        return totals

    def failure_reasons(self, run_id: str) -> dict[str, int]:
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT candidate_json FROM authoring_attempts
                WHERE run_id = ? AND candidate_status IN (?, ?)
                """,
                (run_id, CandidateStatus.REJECTED.value, CandidateStatus.FAILED.value),
            ).fetchall()
        reasons: dict[str, int] = {}
        for row in rows:
            candidate = AuthoredCandidate.model_validate_json(row["candidate_json"])
            if candidate.error_stage:
                reason = candidate.error_stage
            else:
                failed = next(
                    (gate.gate for gate in reversed(candidate.gates) if gate.required and not gate.passed),
                    "unknown",
                )
                reason = failed
            reasons[reason] = reasons.get(reason, 0) + 1
        return dict(sorted(reasons.items()))

    def next_ready_delay(self, run_id: str) -> float | None:
        with self._lock:
            row = self.conn.execute(
                """
                SELECT MIN(next_attempt_at) AS next_at FROM authoring_items
                WHERE run_id = ? AND status = ?
                """,
                (run_id, ItemStatus.PENDING.value),
            ).fetchone()
        if not row or not row["next_at"]:
            return None
        ready = datetime.fromisoformat(row["next_at"])
        return max(0.0, (ready - _now()).total_seconds())

    @staticmethod
    def item_output_dir(output_root: Path, run_id: str, spec: GenerationSpec) -> Path:
        return output_root / "runs" / run_id / "items" / f"{spec.ordinal:06d}-{spec.spec_id[:12]}"

    def write_candidate_artifacts(self, claimed: ClaimedItem, candidate: AuthoredCandidate) -> tuple[Path, str]:
        attempt_dir = claimed.output_dir / "attempts" / f"attempt-{claimed.attempt:03d}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(
            attempt_dir / "spec.json",
            json.dumps(claimed.spec.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        )
        _atomic_write(
            attempt_dir / "candidate.json",
            json.dumps(candidate.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        )
        if candidate.problem_latex:
            _atomic_write(attempt_dir / "problem.tex", candidate.problem_latex.rstrip() + "\n")
        if candidate.draft_solution_latex:
            _atomic_write(attempt_dir / "draft_solution.tex", candidate.draft_solution_latex.rstrip() + "\n")
        if candidate.final_latex:
            _atomic_write(attempt_dir / "final.tex", candidate.final_latex.rstrip() + "\n")
        if candidate.diagram_code:
            _atomic_write(attempt_dir / "diagram.tex", candidate.diagram_code.rstrip() + "\n")

        artifact_content = _candidate_artifact_content(candidate)
        artifact_sha256 = hashlib.sha256(artifact_content.encode()).hexdigest()
        return attempt_dir, artifact_sha256

    @staticmethod
    def _promote_candidate_artifacts(
        claimed: ClaimedItem,
        candidate: AuthoredCandidate,
    ) -> list[Path]:
        """Publish a passing artifact, returning only paths created in this call."""
        if not candidate.final_latex:
            raise ValueError(
                f"passing candidate {claimed.spec.spec_id} has no final LaTeX"
            )
        candidate_json = (
            json.dumps(candidate.model_dump(mode="json"), indent=2, sort_keys=True)
            + "\n"
        )
        spec_json = (
            json.dumps(claimed.spec.model_dump(mode="json"), indent=2, sort_keys=True)
            + "\n"
        )
        final_latex = candidate.final_latex.rstrip() + "\n"
        collection = (
            "accepted"
            if candidate.status is CandidateStatus.ACCEPTED
            else "drafts" if candidate.status is CandidateStatus.DRAFT else "needs_review"
        )
        run_dir = claimed.output_dir.parent.parent
        targets: list[tuple[Path, str]] = [
            (claimed.output_dir / "spec.json", spec_json),
            (claimed.output_dir / "candidate.json", candidate_json),
            (claimed.output_dir / "problem.tex", final_latex),
            (
                run_dir
                / collection
                / f"problem_{claimed.spec.ordinal:06d}_{claimed.spec.spec_id[:12]}.tex",
                final_latex,
            ),
        ]
        created: list[Path] = []
        try:
            for path, content in targets:
                if _write_immutable(path, content):
                    created.append(path)
        except Exception:
            for path in reversed(created):
                path.unlink(missing_ok=True)
            raise
        return created

    def write_generated_manifest(self, run_id: str) -> Path | None:
        """Describe the accepted-only publication view for a finished run."""
        run = self.get_run(run_id)
        stats = self.stats(run_id)
        terminal = run["status"] in {
            RunStatus.COMPLETED.value,
            RunStatus.CANCELLED.value,
        }
        if not terminal and not any(
            stats[status] for status in (ItemStatus.ACCEPTED.value, ItemStatus.DRAFT.value, ItemStatus.NEEDS_REVIEW.value)
        ):
            return None

        with self._lock:
            rows = self.conn.execute(
                """
                SELECT spec_id, ordinal, spec_json, status, artifact_sha256, completed_at
                FROM authoring_items
                WHERE run_id = ? AND status IN (?, ?, ?)
                ORDER BY ordinal
                """,
                (run_id, ItemStatus.ACCEPTED.value, ItemStatus.DRAFT.value, ItemStatus.NEEDS_REVIEW.value),
            ).fetchall()

        output_root = Path(run["output_dir"])
        artifacts: list[dict[str, Any]] = []
        from vbagent.authoring.exports import get_export

        for row in rows:
            spec = GenerationSpec.model_validate_json(row["spec_json"])
            exported = get_export(self, spec.spec_id)
            path = generated_output_root(output_root) / f"problem_{exported['number']}.tex" if exported else None
            artifacts.append(
                {
                    "ordinal": spec.ordinal,
                    "spec_id": spec.spec_id,
                    "exam": spec.exam,
                    "subject": spec.subject,
                    "chapter_id": spec.chapter_id,
                    "chapter": spec.chapter,
                    "topic_id": spec.topic_id,
                    "topic": spec.topic,
                    "question_type": spec.question_type.value,
                    "artifact_sha256": row["artifact_sha256"],
                    "completed_at": row["completed_at"],
                    "status": row["status"],
                    "path": str(path) if path and path.is_file() else None,
                }
            )

        scope = self.run_scope(run_id)
        build_path = generated_build_path(output_root, run_id)
        publication = (
            json.loads(build_path.read_text(encoding="utf-8"))
            if build_path.is_file()
            else None
        )
        manifest = {
            "run_id": run_id,
            "status": run["status"],
            **scope,
            "stats": stats,
            "progress": self.run_progress(run_id),
            "generated_output_dir": str(generated_output_root(output_root)),
            "publication": publication,
            "artifacts": artifacts,
            "updated_at": run["updated_at"],
        }
        path = generated_manifest_path(output_root, run_id)
        _atomic_write(path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return path

    def write_run_manifest(self, run_id: str) -> Path:
        run = self.get_run(run_id)
        stats = self.stats(run_id)
        plan = self.plan_metadata(run_id)
        generated_manifest = self.write_generated_manifest(run_id)
        manifest = {
            "run_id": run_id,
            "status": run["status"],
            "catalog_version": run["catalog_version"],
            "catalog_source_url": plan["catalog_source_url"],
            "catalog_verified_at": plan["catalog_verified_at"],
            "catalog_source_sha256": run["catalog_source_sha256"],
            "allowed_question_types": [
                str(question_type) for question_type in plan["allowed_question_types"]
            ],
            "exam_pattern_description": plan["exam_pattern_description"],
            "exam_pattern_source_url": plan["exam_pattern_source_url"],
            "exam_pattern_verified_at": plan["exam_pattern_verified_at"],
            "plan_sha256": run["plan_sha256"],
            "stats": stats,
            "progress": self.run_progress(run_id),
            "accepted_coverage": self.accepted_coverage(run_id),
            "usage": self.usage_summary(run_id),
            "failure_reasons": self.failure_reasons(run_id),
            "generated_output_dir": str(
                generated_output_root(Path(run["output_dir"]))
            ),
            "generated_manifest_path": (
                str(generated_manifest) if generated_manifest is not None else None
            ),
            "updated_at": run["updated_at"],
        }
        path = Path(run["output_dir"]) / "runs" / run_id / "run.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return path


def _compact_plan_json(plan: AuthoringPlan) -> str:
    """Serialize run metadata once; item specs live canonically in their rows."""
    payload = plan.model_dump(mode="json", exclude={"items"})
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _plan_sha256(plan: AuthoringPlan) -> str:
    """Hash a plan incrementally so large runs do not need a second full copy."""
    digest = hashlib.sha256(b"vbagent-authoring-plan-v2\0")
    digest.update(_compact_plan_json(plan).encode())
    for spec in plan.items:
        digest.update(b"\0")
        digest.update(
            json.dumps(
                spec.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
    return digest.hexdigest()


def _legacy_plan_sha256(plan: AuthoringPlan) -> str:
    payload = json.dumps(
        plan.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _write_immutable(path: Path, content: str) -> bool:
    """Write once, accepting an idempotent replay but never a mismatch."""
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(
                f"refusing to overwrite mismatched promoted artifact {path}"
            )
        return False
    _atomic_write(path, content)
    return True


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _candidate_artifact_content(candidate: AuthoredCandidate) -> str:
    return candidate.final_latex or candidate.problem_latex or candidate.model_dump_json()
