"""One authoritative problem-authoring and acceptance pipeline."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from vbagent.authoring.agents import DefaultAuthoringAgents
from vbagent.authoring.models import (
    DiagramPolicy,
    GenerationSpec,
    SourceKind,
    VariantFamily,
)
from vbagent.authoring.novelty import NoveltyIndex
from vbagent.authoring.results import AuthoredCandidate, CandidateStatus, GateResult
from vbagent.authoring.structure import (
    validate_draft_structure,
    validate_final_structure,
)
from vbagent.pipeline.io import (
    has_main_diagram_placeholder,
    replace_main_diagram_placeholder,
)

logger = logging.getLogger(__name__)


class AuthoringPipeline:
    """Run a GenerationSpec through every required acceptance gate."""

    CONTRACT_VERSION = 2

    def __init__(
        self,
        agents: Any | None = None,
        novelty_index: NoveltyIndex | None = None,
        render_dir: str | Path | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ):
        self.agents = agents or DefaultAuthoringAgents()
        self.novelty_index = novelty_index or NoveltyIndex()
        self.render_dir = str(Path(render_dir).resolve()) if render_dir else None
        self.progress_callback = progress_callback

    def run(self, spec: GenerationSpec, retry_context: str | None = None) -> AuthoredCandidate:
        from vbagent.ui.logging import (
            agent_logging_context,
            agent_task_context,
            capture_agent_logging_context,
        )

        events: list[dict[str, Any]] = []
        current_logging = capture_agent_logging_context()
        with agent_task_context(
            f"item {spec.ordinal:03d} · {spec.spec_id[:8]}"
        ), agent_logging_context(
            output_console=current_logging.console,
            quiet=current_logging.quiet,
            event_sink=events.append,
        ):
            candidate = self._run(spec, retry_context=retry_context)
        candidate.provenance["usage"] = _aggregate_usage(events)
        return candidate

    def _run(self, spec: GenerationSpec, retry_context: str | None = None) -> AuthoredCandidate:
        candidate = AuthoredCandidate(
            spec=spec,
            status=CandidateStatus.RUNNING,
            provenance={
                "authoring_contract_version": self.CONTRACT_VERSION,
                "spec_fingerprint": spec.fingerprint(),
                "agents": self.agents.provenance() if hasattr(self.agents, "provenance") else {},
            },
        )

        self._progress("drafting")
        try:
            draft, elapsed = _timed(
                self.agents.generate_draft,
                spec,
                **({"retry_context": retry_context} if retry_context else {}),
            )
        except Exception as exc:
            return self._fail(candidate, "draft", exc)
        candidate.problem_latex = draft.problem_latex.strip()
        candidate.draft_solution_latex = draft.solution_latex.strip() if spec.include_solution else ""
        candidate.idea_latex = (getattr(draft, "idea_latex", "") or "").strip() if spec.include_idea else ""
        candidate.diagram_description = (getattr(draft, "diagram_description", "") or "").strip()
        candidate.generation_metadata = dict(getattr(draft, "generation_metadata", {}) or {})
        candidate.gates.append(
            GateResult(gate="draft", passed=True, summary="draft generated", duration_ms=elapsed)
        )

        self._progress("validating_draft_structure")
        structure_issues = validate_draft_structure(
            spec,
            candidate.problem_latex,
            candidate.draft_solution_latex,
            candidate.diagram_description,
        )
        if spec.include_idea and not re.search(r"\\begin\{idea\}.*?\\end\{idea\}", candidate.idea_latex, re.DOTALL):
            structure_issues.append("requested idea component must contain a complete idea environment")
        if not self._gate(
            candidate,
            gate="structure",
            required=True,
            passed=not structure_issues,
            summary="draft structure is valid" if not structure_issues else "; ".join(structure_issues),
            data={"issues": structure_issues},
        ):
            return self._reject(candidate)

        if candidate.diagram_description and spec.diagram_policy is not DiagramPolicy.FORBIDDEN:
            self._progress("generating_problem_diagram")
            try:
                diagram, elapsed = _timed(
                    self.agents.generate_problem_diagram,
                    spec,
                    candidate.problem_latex,
                    candidate.diagram_description,
                )
            except Exception as exc:
                return self._fail(candidate, "problem_diagram", exc)
            candidate.diagram_code = (diagram.get("code") or "").strip()
            if not candidate.diagram_code:
                return self._fail(candidate, "problem_diagram", RuntimeError("diagram agent returned no code"))
            candidate.problem_latex = _assemble_problem_diagram(
                candidate.problem_latex,
                candidate.diagram_code,
            )
            candidate.gates.append(
                GateResult(
                    gate="problem_diagram",
                    passed=True,
                    summary=f"problem diagram generated by {diagram.get('agent', 'unknown')}",
                    data={"agent": diagram.get("agent")},
                    duration_ms=elapsed,
                )
            )

        if not spec.include_solution:
            candidate.final_latex = "\n\n".join(part for part in (candidate.problem_latex, candidate.idea_latex) if part)
            issues = validate_final_structure(spec, candidate.final_latex)
            if not self._gate(candidate, gate="final_structure", required=True, passed=not issues, summary="draft components are complete" if not issues else "; ".join(issues)):
                return self._reject(candidate)
            self._progress("compiling_item")
            try:
                result, elapsed = _timed(self.agents.compile, spec, candidate.final_latex, self.render_dir)
            except Exception as exc:
                return self._fail(candidate, "compile", exc)
            if not self._gate(candidate, gate="compile", required=True, passed=bool(result.get("success")), summary=result.get("error_summary") or "draft compiled; correctness checks are deferred", data=result, duration_ms=elapsed):
                return self._reject(candidate)
            candidate.status = CandidateStatus.DRAFT
            candidate.provenance["deferred_checks"] = ["independent_solution", "answer_agreement", "spec_alignment", "difficulty", "review", "novelty"]
            candidate.completed_at = _now()
            return candidate

        self._progress("solving_independently")
        try:
            solved, elapsed = _timed(
                self.agents.solve_independently,
                spec,
                candidate.problem_latex,
                bool(candidate.diagram_code) or bool(re.search(
                    r"\\(?:begin\{(?:tikzpicture|circuitikz|axis)\}|includegraphics)",
                    candidate.problem_latex,
                )),
            )
        except Exception as exc:
            return self._fail(candidate, "independent_solution", exc)
        independent_latex = re.sub(
            r"\\begin\{idea\}.*?\\end\{idea\}", "", solved.latex, flags=re.DOTALL
        ).strip()
        candidate.independent_solution_latex = _extract_solution(independent_latex)
        candidate.final_latex = independent_latex
        if spec.source_kind is SourceKind.COMPLETION:
            if spec.parent_solution_latex:
                # A fresh solve is verification evidence, not permission to rewrite
                # the author's saved solution or its alternate methods.
                candidate.final_latex = spec.parent_final_latex or (
                    candidate.problem_latex + "\n\n" + spec.parent_solution_latex
                )
            else:
                marker = re.search(r"\\begin\{solution\}", independent_latex)
                if marker:
                    candidate.final_latex = candidate.problem_latex.rstrip() + "\n\n" + independent_latex[marker.start():]
        if not candidate.independent_solution_latex:
            return self._fail(candidate, "independent_solution", ValueError("independent solver returned no complete solution"))
        candidate.provenance["independent_answer"] = {
            "answer_type": getattr(solved, "answer_type", None),
            "answer_value": getattr(solved, "answer_value", None),
            "final_answer_latex": getattr(solved, "final_answer_latex", None),
        }
        candidate.gates.append(
            GateResult(
                gate="independent_solution",
                passed=True,
                summary="independent solution generated",
                duration_ms=elapsed,
            )
        )

        self._progress("validating_final_structure")
        final_issues = validate_final_structure(spec, candidate.final_latex)
        if not self._gate(
            candidate,
            gate="final_structure",
            required=True,
            passed=not final_issues,
            summary="assembled artifact is structurally complete" if not final_issues else "; ".join(final_issues),
            data={"issues": final_issues},
        ):
            return self._reject(candidate)

        self._progress("classifying_problem")
        try:
            primary, elapsed = _timed(self.agents.classify, spec, candidate.problem_latex)
        except Exception as exc:
            return self._fail(candidate, "classification", exc)
        candidate.classification = primary.model_dump(mode="json")
        classification_passed = (
            primary.subject == spec.subject and primary.question_type == spec.question_type.value
        )
        if not self._gate(
            candidate,
            gate="classification",
            required=True,
            passed=classification_passed,
            summary=(
                "independent subject/type classification matches the specification"
                if classification_passed
                else f"classified as {primary.subject}/{primary.question_type}, expected "
                f"{spec.subject}/{spec.question_type.value}"
            ),
            data=candidate.classification,
            duration_ms=elapsed,
        ):
            return self._reject(candidate)

        self._progress("adjudicating_answer")
        try:
            agreement, elapsed = _timed(
                self.agents.verify_answer,
                spec,
                candidate.problem_latex,
                candidate.draft_solution_latex,
                candidate.independent_solution_latex,
            )
        except Exception as exc:
            return self._fail(candidate, "answer_agreement", exc)
        candidate.answer_agreement = agreement.model_dump(mode="json")
        if not self._gate(
            candidate,
            gate="answer_agreement",
            required=True,
            passed=agreement.passed,
            summary=agreement.reasoning,
            data=candidate.answer_agreement,
            duration_ms=elapsed,
        ):
            return self._reject(candidate)

        self._progress("checking_syllabus_alignment")
        try:
            alignment, elapsed = _timed(
                self.agents.verify_spec,
                spec,
                candidate.problem_latex,
                _extract_solution(candidate.final_latex),
            )
        except Exception as exc:
            return self._fail(candidate, "spec_alignment", exc)
        candidate.spec_alignment = alignment.model_dump(mode="json")
        if not self._gate(
            candidate,
            gate="spec_alignment",
            required=True,
            passed=alignment.passed,
            summary=alignment.reasoning,
            data=candidate.spec_alignment,
            duration_ms=elapsed,
        ):
            return self._reject(candidate)

        self._progress("assessing_difficulty")
        try:
            difficulty, elapsed = _timed(
                self.agents.assess_difficulty,
                spec,
                candidate.final_latex,
                primary,
            )
        except Exception as exc:
            return self._fail(candidate, "difficulty", exc)
        candidate.difficulty = difficulty.model_dump(mode="json")
        observed = float(difficulty.difficulty_score)
        tolerance = spec.acceptance.difficulty_tolerance
        difficulty_passed = abs(observed - spec.difficulty) <= tolerance
        if not self._gate(
            candidate,
            gate="difficulty",
            required=True,
            passed=difficulty_passed,
            summary=f"observed difficulty {observed:.1f}/10; target {spec.difficulty}/10 ± {tolerance}",
            data=candidate.difficulty,
            duration_ms=elapsed,
        ):
            return self._reject(candidate)

        if candidate.idea_latex and candidate.idea_latex not in candidate.final_latex:
            candidate.final_latex = candidate.final_latex.rstrip() + "\n\n" + candidate.idea_latex

        self._progress("compiling_item")
        try:
            compile_result, elapsed = _timed(
                self.agents.compile,
                spec,
                candidate.final_latex,
                self.render_dir,
            )
        except Exception as exc:
            return self._fail(candidate, "compile", exc)
        if not self._gate(
            candidate,
            gate="compile",
            required=True,
            passed=bool(compile_result.get("success")),
            summary=(compile_result.get("error_summary") or "LaTeX compiled successfully"),
            data=compile_result,
            duration_ms=elapsed,
        ):
            return self._reject(candidate)

        self._progress("reviewing_quality")
        try:
            review, elapsed = _timed(self.agents.review, spec, candidate.final_latex)
        except Exception as exc:
            return self._fail(candidate, "review", exc)
        candidate.review = review.model_dump(mode="json")
        if not self._gate(
            candidate,
            gate="review",
            required=True,
            passed=bool(review.passed),
            summary=review.summary,
            data=candidate.review,
            duration_ms=elapsed,
        ):
            return self._reject(candidate)

        self._progress("checking_novelty")
        if spec.source_kind is SourceKind.COMPLETION and spec.parent_was_accepted:
            from types import SimpleNamespace

            novelty = SimpleNamespace(passed=True, mode="unchanged_completion", max_similarity=0.0, closest_id=spec.parent_spec_id)
            elapsed = 0
        elif spec.source_kind is SourceKind.VARIANT:
            exact_only = spec.variant_family is VariantFamily.NUMERICAL
            if spec.acceptance.human_review_required:
                novelty, elapsed = _timed(
                    self.novelty_index.check_variant,
                    candidate.problem_latex,
                    spec.acceptance.novelty_threshold,
                    parent_id=spec.parent_spec_id,
                    exact_only=exact_only,
                )
            else:
                novelty, elapsed = _timed(
                    self.novelty_index.check_variant_and_add,
                    spec.spec_id,
                    candidate.problem_latex,
                    spec.acceptance.novelty_threshold,
                    parent_id=spec.parent_spec_id,
                    exact_only=exact_only,
                )
        else:
            novelty_function = (
                self.novelty_index.check
                if spec.acceptance.human_review_required
                else self.novelty_index.check_and_add
            )
            novelty_args = (
                (candidate.problem_latex, spec.acceptance.novelty_threshold)
                if spec.acceptance.human_review_required
                else (spec.spec_id, candidate.problem_latex, spec.acceptance.novelty_threshold)
            )
            novelty, elapsed = _timed(novelty_function, *novelty_args)
        if novelty.mode == "exact_variant":
            novelty_summary = (
                "variant artifact is unique among accepted artifacts"
                if novelty.passed
                else f"variant artifact duplicates accepted item {novelty.closest_id}"
            )
        else:
            novelty_summary = (
                f"maximum blueprint similarity {novelty.max_similarity:.3f}"
                + (f" to {novelty.closest_id}" if novelty.closest_id else "")
            )
        if not self._gate(
            candidate,
            gate="novelty",
            required=True,
            passed=novelty.passed,
            summary=novelty_summary,
            data={
                "max_similarity": novelty.max_similarity,
                "closest_id": novelty.closest_id,
                "threshold": (
                    None
                    if novelty.mode == "exact_variant"
                    else spec.acceptance.novelty_threshold
                ),
                "mode": novelty.mode,
            },
            duration_ms=elapsed,
        ):
            return self._reject(candidate)

        self._progress("finalizing_item")
        candidate.status = (
            CandidateStatus.NEEDS_REVIEW
            if spec.acceptance.human_review_required
            else CandidateStatus.ACCEPTED
        )
        candidate.completed_at = _now()
        return candidate

    def _progress(self, stage: str) -> None:
        """Publish best-effort progress without coupling acceptance to telemetry."""
        if self.progress_callback is None:
            return
        try:
            self.progress_callback(stage)
        except Exception:  # noqa: BLE001 - progress must not corrupt authored work
            logger.warning("could not persist authoring stage %s", stage, exc_info=True)

    @staticmethod
    def _gate(
        candidate: AuthoredCandidate,
        *,
        gate: str,
        required: bool,
        passed: bool,
        summary: str,
        data: dict[str, Any] | None = None,
        duration_ms: int = 0,
    ) -> bool:
        candidate.gates.append(
            GateResult(
                gate=gate,
                required=required,
                passed=passed,
                summary=summary,
                data=data or {},
                duration_ms=duration_ms,
            )
        )
        return passed or not required

    @staticmethod
    def _reject(candidate: AuthoredCandidate) -> AuthoredCandidate:
        candidate.status = CandidateStatus.REJECTED
        candidate.completed_at = _now()
        return candidate

    @staticmethod
    def _fail(candidate: AuthoredCandidate, stage: str, exc: Exception) -> AuthoredCandidate:
        candidate.status = CandidateStatus.FAILED
        candidate.error_stage = stage
        candidate.error_message = f"{type(exc).__name__}: {exc}"
        candidate.completed_at = _now()
        candidate.gates.append(
            GateResult(
                gate=stage,
                passed=False,
                summary=candidate.error_message,
                data={"exception_type": type(exc).__name__},
            )
        )
        return candidate


def _assemble_problem_diagram(problem_latex: str, diagram_code: str) -> str:
    if has_main_diagram_placeholder(problem_latex):
        return replace_main_diagram_placeholder(problem_latex, diagram_code)
    return problem_latex.rstrip() + "\n\n\\begin{center}\n" + diagram_code.strip() + "\n\\end{center}"


def _extract_solution(final_latex: str) -> str:
    match = re.search(r"\\begin\{solution\}.*?\\end\{solution\}", final_latex, re.DOTALL)
    return match.group(0).strip() if match else ""


def _timed(function: Callable, *args, **kwargs):
    started = time.perf_counter()
    result = function(*args, **kwargs)
    elapsed = max(0, round((time.perf_counter() - started) * 1000))
    return result, elapsed


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_CACHE_USAGE_BUCKET_FIELDS = (
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


def _empty_cache_usage_bucket() -> dict[str, int]:
    return {field: 0 for field in _CACHE_USAGE_BUCKET_FIELDS}


def _finalize_cache_usage_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
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


def _aggregate_usage(events: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [event for event in events if event.get("event") == "completed"]
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
        "profile_failovers": sum(
            1 for event in events if event.get("event") == "profile_failover"
        ),
    }
    by_agent: list[dict[str, Any]] = []
    profiles: dict[str, int] = {}
    cache_domains: dict[str, int] = {}
    profile_usage: dict[str, dict[str, Any]] = {}
    cache_domain_usage: dict[str, dict[str, Any]] = {}
    for event in completed:
        tokens = event.get("tokens") or {}
        requests = int(tokens.get("requests", 0) or 0)
        totals["requests"] += requests
        totals["input_tokens"] += int(tokens.get("input", 0) or 0)
        totals["output_tokens"] += int(tokens.get("output", 0) or 0)
        totals["cached_tokens"] += int(tokens.get("cached", 0) or 0)
        totals["cache_write_tokens"] += int(tokens.get("cache_write", 0) or 0)
        totals["ordinary_input_tokens"] += int(tokens.get("ordinary_input", 0) or 0)
        totals["cache_read_requests"] += int(tokens.get("cache_read_requests", 0) or 0)
        totals["cache_reported_requests"] += int(tokens.get("cache_reported_requests", 0) or 0)
        totals["cache_metrics_reported_calls"] += int(
            bool(tokens.get("cache_metrics_reported", False))
        )
        if tokens.get("cache_metrics_reported", False):
            totals["cache_metrics_reported_input_tokens"] += int(
                tokens.get("input", 0) or 0
            )
        effective_multiplier = tokens.get("effective_input_multiplier")
        if effective_multiplier is not None:
            event_input = int(tokens.get("input", 0) or 0)
            totals["effective_input_eligible_tokens"] += event_input
            totals["effective_input_cost_units"] += (
                float(effective_multiplier) * event_input
            )
        totals["reasoning_tokens"] += int(tokens.get("reasoning", 0) or 0)
        totals["duration_seconds"] += float(event.get("duration", 0.0) or 0.0)
        attributed_requests = requests or 1
        if event.get("key_name"):
            name = str(event["key_name"])
            profiles[name] = profiles.get(name, 0) + attributed_requests
            _accumulate_cache_usage_bucket(
                profile_usage.setdefault(name, _empty_cache_usage_bucket()),
                tokens,
                attributed_requests,
            )
        if event.get("cache_domain"):
            domain = str(event["cache_domain"])
            cache_domains[domain] = cache_domains.get(domain, 0) + attributed_requests
            _accumulate_cache_usage_bucket(
                cache_domain_usage.setdefault(domain, _empty_cache_usage_bucket()),
                tokens,
                attributed_requests,
            )
        by_agent.append(
            {
                "agent": event.get("agent"),
                "stage": event.get("stage"),
                "model": event.get("model"),
                "reasoning_effort": event.get("reasoning_effort"),
                "duration_seconds": event.get("duration", 0.0),
                "request_duration_seconds": event.get("request_duration", 0.0),
                "queue_duration_seconds": event.get("queue_duration", 0.0),
                "tokens": tokens,
                "key_name": event.get("key_name"),
                "cache_domain": event.get("cache_domain"),
                "cache_group_id": event.get("cache_group_id"),
                "response_id": event.get("response_id"),
            }
        )
    totals["duration_seconds"] = round(totals["duration_seconds"], 4)
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
    for event in events:
        if event.get("event") != "profile_failover":
            continue
        if event.get("key_name"):
            bucket = profile_usage.setdefault(
                str(event["key_name"]),
                _empty_cache_usage_bucket(),
            )
            bucket["failovers"] += 1
        if event.get("cache_domain"):
            bucket = cache_domain_usage.setdefault(
                str(event["cache_domain"]),
                _empty_cache_usage_bucket(),
            )
            bucket["failovers"] += 1
    return {
        "totals": totals,
        "agents": by_agent,
        "profiles": profiles,
        "cache_domains": cache_domains,
        "profile_usage": {
            name: _finalize_cache_usage_bucket(bucket)
            for name, bucket in profile_usage.items()
        },
        "cache_domain_usage": {
            name: _finalize_cache_usage_bucket(bucket)
            for name, bucket in cache_domain_usage.items()
        },
    }


def _accumulate_cache_usage_bucket(
    bucket: dict[str, Any],
    tokens: dict[str, Any],
    attributed_requests: int,
) -> None:
    bucket["requests"] += attributed_requests
    bucket["input_tokens"] += int(tokens.get("input", 0) or 0)
    bucket["output_tokens"] += int(tokens.get("output", 0) or 0)
    bucket["cached_tokens"] += int(tokens.get("cached", 0) or 0)
    bucket["cache_write_tokens"] += int(tokens.get("cache_write", 0) or 0)
    bucket["ordinary_input_tokens"] += int(tokens.get("ordinary_input", 0) or 0)
    bucket["cache_read_requests"] += int(tokens.get("cache_read_requests", 0) or 0)
    bucket["cache_reported_requests"] += int(
        tokens.get("cache_reported_requests", 0) or 0
    )
    if tokens.get("cache_metrics_reported", False):
        bucket["cache_metrics_reported_input_tokens"] += int(
            tokens.get("input", 0) or 0
        )
    effective_multiplier = tokens.get("effective_input_multiplier")
    if effective_multiplier is not None:
        event_input = int(tokens.get("input", 0) or 0)
        bucket["effective_input_eligible_tokens"] += event_input
        bucket["effective_input_cost_units"] += (
            float(effective_multiplier) * event_input
        )
