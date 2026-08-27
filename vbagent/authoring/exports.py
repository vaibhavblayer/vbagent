"""Owned, numbered human copies; the immutable ledger remains authoritative."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from vbagent.authoring.models import GenerationSpec
from vbagent.authoring.paths import generated_output_root, generated_problem_path
from vbagent.authoring.results import AuthoredCandidate

if TYPE_CHECKING:
    from vbagent.authoring.store import AuthoringStore


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def assert_regular_owned_path(path: Path, root: Path) -> None:
    """Do not follow user-controlled links when reading or replacing exports."""
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"refusing non-regular publication path: {path}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"publication path escapes its output folder: {path}")


def atomic_bytes(path: Path, content: bytes, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive:
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode()


@contextmanager
def publication_lock(authoring_root: Path) -> Iterator[None]:
    """Serialize only publication, with a bounded wait and crash-safe OS lock."""
    root = generated_output_root(authoring_root)
    if root.is_symlink():
        raise ValueError(f"generated output folder must not be a symlink: {root}")
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".publication.lock"
    assert_regular_owned_path(lock_path, root)
    with lock_path.open("a+b") as handle:
        deadline = time.monotonic() + 45
        if os.name == "nt":  # pragma: no cover - exercised on Windows
            import msvcrt

            if not lock_path.stat().st_size:
                handle.write(b"0")
                handle.flush()

            def acquire() -> None:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

            def release() -> None:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            def acquire() -> None:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release() -> None:
                fcntl.flock(handle, fcntl.LOCK_UN)

        while True:
            try:
                acquire()
                break
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "another publication is still running; retry shortly"
                    ) from None
                time.sleep(0.05)
        try:
            yield
        finally:
            release()


def get_export(
    store: AuthoringStore, spec_id: str, *, follow_parents: bool = False
) -> dict[str, Any] | None:
    with store._lock:
        seen = set()
        while spec_id not in seen:
            seen.add(spec_id)
            row = store.conn.execute(
                "SELECT * FROM authoring_exports WHERE current_spec_id = ? OR source_spec_id = ?",
                (spec_id, spec_id),
            ).fetchone()
            if row:
                return dict(row)
            if not follow_parents:
                break
            item = store.conn.execute(
                "SELECT spec_json FROM authoring_items WHERE spec_id = ?", (spec_id,)
            ).fetchone()
            spec = json.loads(item["spec_json"]) if item else {}
            if spec.get("source_kind") != "completion" or not spec.get(
                "parent_spec_id"
            ):
                break
            spec_id = spec["parent_spec_id"]
    return None


def exported_items(store: AuthoringStore, authoring_root: Path) -> list[dict[str, Any]]:
    with store._lock:
        rows = store.conn.execute(
            "SELECT metadata_json FROM authoring_exports WHERE output_root = ? "
            "AND metadata_json IS NOT NULL ORDER BY number",
            (str(generated_output_root(authoring_root)),),
        ).fetchall()
    return [json.loads(row["metadata_json"]) for row in rows]


def export_item(store: AuthoringStore, run_id: str, spec_id: str) -> dict[str, Any]:
    root = Path(store.get_run(run_id)["output_dir"])
    with publication_lock(root):
        return _export_item_locked(store, run_id, spec_id)


def _export_item_locked(
    store: AuthoringStore, run_id: str, spec_id: str
) -> dict[str, Any]:
    item = store.get_run_item(run_id, spec_id)
    if item["status"] not in {"accepted", "draft", "needs_review", "rejected"}:
        raise ValueError(f"item {spec_id} has no publishable draft")
    candidate = AuthoredCandidate.model_validate_json(item["last_candidate_json"])
    spec = GenerationSpec.model_validate_json(item["spec_json"])
    content = candidate.deliverable_latex
    if not content.strip():
        raise ValueError(f"item {spec_id} has no authored content")
    content_bytes = (content.rstrip() + "\n").encode()
    authoring_root = Path(store.get_run(run_id)["output_dir"])
    output_root = generated_output_root(authoring_root)
    parent_id = spec.parent_spec_id if spec.source_kind.value == "completion" else None
    if parent_id and item["status"] in {"needs_review", "rejected"}:
        # An unsuccessful addition must not replace the author's previous file.
        review_path = store.item_output_dir(authoring_root, run_id, spec) / "review.tex"
        assert_regular_owned_path(review_path, authoring_root)
        atomic_bytes(review_path, content_bytes)
        return {
            "run_id": run_id,
            "spec_id": spec_id,
            "status": item["status"],
            "validated": False,
            "path": str(review_path),
        }
    with store._transaction() as conn:
        row = conn.execute(
            "SELECT * FROM authoring_exports WHERE current_spec_id = ? OR source_spec_id = ?",
            (spec_id, spec_id),
        ).fetchone()
        if row is None and parent_id:
            row = get_export(store, parent_id, follow_parents=True)
            if row is None:
                raise ValueError(
                    "completion source has changed or has not been exported"
                )
        if row is None:
            number = conn.execute(
                "SELECT COALESCE(MAX(number), 0) + 1 FROM authoring_exports WHERE output_root = ?",
                (str(output_root),),
            ).fetchone()[0]
            while any(
                os.path.lexists(
                    generated_problem_path(authoring_root, number).with_suffix(suffix)
                )
                for suffix in (".tex", ".json")
            ):
                number += 1
            conn.execute(
                "INSERT INTO authoring_exports (source_spec_id, current_spec_id, output_root, number) VALUES (?, ?, ?, ?)",
                (spec_id, spec_id, str(output_root), number),
            )
            row = conn.execute(
                "SELECT * FROM authoring_exports WHERE source_spec_id = ?", (spec_id,)
            ).fetchone()
    record = dict(row)
    if record["current_spec_id"] not in {spec_id, parent_id}:
        if record["metadata_json"]:
            return json.loads(record["metadata_json"])
        raise ValueError("a newer completion owns this problem file")
    path = generated_problem_path(authoring_root, record["number"])
    metadata_path = path.with_suffix(".json")
    assert_regular_owned_path(path, output_root)
    assert_regular_owned_path(metadata_path, output_root)
    previous_metadata = (
        json.loads(record["metadata_json"]) if record["metadata_json"] else None
    )
    metadata = {
        "schema_version": 1,
        "number": record["number"],
        "run_id": run_id,
        "spec_id": spec_id,
        "source_spec_id": record["source_spec_id"],
        "ordinal": spec.ordinal,
        "status": item["status"],
        "validated": item["status"] == "accepted",
        "path": str(path),
        "metadata_path": str(metadata_path),
        "content_sha256": digest(content_bytes),
        "specification": spec.model_dump(mode="json"),
        "gates": [gate.model_dump(mode="json") for gate in candidate.gates],
        "review_reason": item.get("human_review_reason"),
    }
    # A completion changes the human copy, never the original run's evidence.
    # The recorded old digest is the only authority to replace an existing file.
    writes = []
    for target, new_bytes, old_digest in (
        (path, content_bytes, record["content_sha256"]),
        (
            metadata_path,
            json_bytes(metadata),
            digest(json_bytes(previous_metadata)) if previous_metadata else None,
        ),
    ):
        if target.exists():
            current = target.read_bytes()
            if current == new_bytes:
                continue
            if not old_digest or digest(current) != old_digest:
                raise ValueError(
                    f"manual edits preserved; refusing to overwrite {target}"
                )
        writes.append((target, new_bytes, not target.exists()))
    for target, new_bytes, exclusive in writes:
        atomic_bytes(target, new_bytes, exclusive=exclusive)
    with store._transaction() as conn:
        conn.execute(
            "UPDATE authoring_exports SET current_spec_id = ?, content_sha256 = ?, metadata_json = ? WHERE source_spec_id = ?",
            (
                spec_id,
                metadata["content_sha256"],
                json.dumps(metadata, sort_keys=True),
                record["source_spec_id"],
            ),
        )
    return metadata


def export_run_locked(store: AuthoringStore, run_id: str) -> list[dict[str, Any]]:
    """Caller holds publication_lock; include review copies but never compile them."""
    result = []
    for item in store.list_items(run_id):
        if (
            item["status"] in {"accepted", "draft", "needs_review"}
            and item["last_candidate_json"]
        ):
            result.append(_export_item_locked(store, run_id, item["spec_id"]))
    return result
