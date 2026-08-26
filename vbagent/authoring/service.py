"""Concurrent, resumable execution service for canonical authoring plans."""

from __future__ import annotations

import os
import socket
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from vbagent.authoring.novelty import NoveltyIndex
from vbagent.authoring.pipeline import AuthoringPipeline
from vbagent.authoring.results import AuthoredCandidate, CandidateStatus, GateResult
from vbagent.authoring.store import AuthoringStore, ClaimedItem, RunStatus


class RunLeaseError(RuntimeError):
    """Raised when another process already owns an active authoring run."""


PipelineFactory = Callable[[ClaimedItem, NoveltyIndex], AuthoringPipeline]


class AuthoringRunService:
    """Execute planned items with durable claims and bounded retries."""

    def __init__(
        self,
        store: AuthoringStore,
        *,
        pipeline_factory: PipelineFactory | None = None,
        retry_base_seconds: float = 2.0,
        run_lease_seconds: int = 3600,
        item_lease_seconds: int = 3600,
    ):
        self.store = store
        self.pipeline_factory = pipeline_factory
        self.retry_base_seconds = max(0.0, retry_base_seconds)
        self.run_lease_seconds = max(60, run_lease_seconds)
        self.item_lease_seconds = max(60, item_lease_seconds)

    def execute(self, run_id: str, *, concurrency: int | None = None) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if run["status"] in {RunStatus.COMPLETED.value, RunStatus.CANCELLED.value}:
            return self.store.stats(run_id)
        workers = concurrency or int(run["concurrency"])
        if workers < 1 or workers > 32:
            raise ValueError("concurrency must be between 1 and 32")

        owner = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}"
        if not self.store.acquire_run_lease(run_id, owner, self.run_lease_seconds):
            current = self.store.get_run(run_id)
            if current["status"] in {RunStatus.COMPLETED.value, RunStatus.CANCELLED.value}:
                return self.store.stats(run_id)
            raise RunLeaseError(f"authoring run {run_id} is already active in another process")

        request = self.store.load_request(run_id)
        novelty = NoveltyIndex()
        for spec_id, problem_latex in self.store.accepted_documents_for_catalog(
            exam=request.exam,
            subject=request.subject,
            catalog_source_sha256=run["catalog_source_sha256"],
        ):
            novelty.add(spec_id, problem_latex)

        stop = threading.Event()
        fatal_errors: list[BaseException] = []
        errors_lock = threading.Lock()
        heartbeat = threading.Thread(
            target=self._heartbeat,
            args=(run_id, owner, stop, fatal_errors, errors_lock),
            name=f"authoring-heartbeat-{run_id[:8]}",
            daemon=True,
        )
        heartbeat.start()

        def worker(worker_number: int) -> None:
            worker_id = f"{owner}:worker-{worker_number}"
            while not stop.is_set():
                try:
                    claimed = self.store.claim_next(
                        run_id,
                        worker_id,
                        lease_seconds=self.item_lease_seconds,
                    )
                except BaseException as exc:
                    with errors_lock:
                        fatal_errors.append(exc)
                    stop.set()
                    return

                if claimed is None:
                    stats = self.store.stats(run_id)
                    if stats["pending"]:
                        delay = self.store.next_ready_delay(run_id)
                        time.sleep(min(max(delay or 0.05, 0.05), 1.0))
                        continue
                    return

                pipeline = self._make_pipeline(claimed, novelty)
                item_stop = threading.Event()
                item_lease_lost = threading.Event()
                item_heartbeat = threading.Thread(
                    target=self._item_heartbeat,
                    args=(claimed, item_stop, item_lease_lost),
                    name=f"authoring-item-heartbeat-{claimed.spec.spec_id[:8]}",
                    daemon=True,
                )
                item_heartbeat.start()
                candidate: AuthoredCandidate | None = None
                try:
                    try:
                        candidate = pipeline.run(
                            claimed.spec,
                            retry_context=claimed.retry_reason,
                        )
                    except BaseException as exc:
                        candidate = AuthoredCandidate(
                            spec=claimed.spec,
                            status=CandidateStatus.FAILED,
                            error_stage="authoring_runner",
                            error_message=f"{type(exc).__name__}: {exc}",
                            gates=[
                                GateResult(
                                    gate="authoring_runner",
                                    passed=False,
                                    summary=f"{type(exc).__name__}: {exc}",
                                )
                            ],
                        )
                    if item_lease_lost.is_set():
                        raise RunLeaseError(
                            f"lost item lease for {claimed.spec.spec_id} attempt {claimed.attempt}"
                        )
                    artifact_dir, artifact_sha256 = self.store.write_candidate_artifacts(
                        claimed,
                        candidate,
                    )
                    self.store.record_candidate(
                        claimed,
                        candidate,
                        artifact_dir=artifact_dir,
                        artifact_sha256=artifact_sha256,
                        retry_base_seconds=self.retry_base_seconds,
                    )
                except BaseException as exc:
                    if candidate is not None and candidate.status is CandidateStatus.ACCEPTED:
                        novelty.remove(claimed.spec.spec_id)
                    try:
                        self.store.abandon_item(
                            claimed,
                            f"{type(exc).__name__}: {exc}",
                        )
                    except Exception:
                        pass
                    with errors_lock:
                        fatal_errors.append(exc)
                    stop.set()
                    return
                finally:
                    item_stop.set()
                    item_heartbeat.join(timeout=5)

        try:
            with ThreadPoolExecutor(
                max_workers=workers,
                thread_name_prefix=f"authoring-{run_id[:8]}",
            ) as executor:
                futures = [executor.submit(worker, index + 1) for index in range(workers)]
                for future in futures:
                    future.result()
        finally:
            stop.set()
            heartbeat.join(timeout=5)
            self.store.refresh_run_status(run_id)
            self.store.release_run_lease(run_id, owner)
            self.store.write_run_manifest(run_id)

        if fatal_errors:
            first = fatal_errors[0]
            raise RuntimeError(
                f"authoring run {run_id} stopped after an infrastructure failure: {first}"
            ) from first
        return self.store.stats(run_id)

    def _make_pipeline(self, claimed: ClaimedItem, novelty: NoveltyIndex) -> AuthoringPipeline:
        if self.pipeline_factory:
            return self.pipeline_factory(claimed, novelty)
        render_dir = claimed.output_dir / "attempts" / f"attempt-{claimed.attempt:03d}" / "render"
        return AuthoringPipeline(
            novelty_index=novelty,
            render_dir=render_dir,
        )

    def _heartbeat(
        self,
        run_id: str,
        owner: str,
        stop: threading.Event,
        fatal_errors: list[BaseException],
        errors_lock: threading.Lock,
    ) -> None:
        interval = min(30.0, self.run_lease_seconds / 3)
        while not stop.wait(interval):
            try:
                if not self.store.renew_run_lease(run_id, owner, self.run_lease_seconds):
                    with errors_lock:
                        fatal_errors.append(RunLeaseError(f"lost run lease for {run_id}"))
                    stop.set()
                    return
            except Exception as exc:
                with errors_lock:
                    fatal_errors.append(exc)
                stop.set()
                return

    def _item_heartbeat(
        self,
        claimed: ClaimedItem,
        stop: threading.Event,
        lease_lost: threading.Event,
    ) -> None:
        interval = min(30.0, self.item_lease_seconds / 3)
        while not stop.wait(interval):
            try:
                renewed = self.store.renew_item_lease(
                    claimed.spec.spec_id,
                    claimed.lease_owner,
                    claimed.attempt,
                    lease_seconds=self.item_lease_seconds,
                )
            except Exception:
                lease_lost.set()
                return
            if not renewed:
                lease_lost.set()
                return

    def cancel(self, run_id: str, reason: str = "user requested cancellation") -> None:
        self.store.request_cancel(run_id, reason)

    def resume(self, run_id: str, *, concurrency: int | None = None) -> dict[str, Any]:
        self.store.resume_run(run_id)
        return self.execute(run_id, concurrency=concurrency)
