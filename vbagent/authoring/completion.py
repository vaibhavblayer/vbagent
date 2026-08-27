"""Plan missing components without regenerating an existing question."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from vbagent.authoring.exports import get_export
from vbagent.authoring.models import AuthoringPlan, GenerationSpec, SourceKind
from vbagent.authoring.results import AuthoredCandidate
from vbagent.authoring.store import AuthoringStore


def plan_completion(
    output_root: Path,
    run_id: str,
    *,
    spec_ids: list[str] | None = None,
    include_solution: bool = True,
    include_idea: bool = True,
) -> AuthoringPlan:
    """Create an immutable child run bound to the exact saved parent content."""
    with AuthoringStore(output_root) as store:
        parent_plan = store.load_plan(run_id)
        rows = store.list_items(run_id)
        selected = set(spec_ids or [])
        if selected - {row["spec_id"] for row in rows}:
            raise ValueError("completion selection contains items from another run")
        parents = [row for row in rows if not selected or row["spec_id"] in selected]
        if not parents:
            raise ValueError("no existing problems were selected")
        provisional = []
        for row in parents:
            exported = get_export(store, row["spec_id"], follow_parents=True)
            if exported and exported["current_spec_id"] != row["spec_id"]:
                row = store.get_item(exported["current_spec_id"])
            if row["status"] not in {"accepted", "draft"}:
                raise ValueError(
                    "review-pending problems need an author decision before component completion"
                )
            parent = GenerationSpec.model_validate_json(row["spec_json"])
            candidate = AuthoredCandidate.model_validate_json(
                row["last_candidate_json"]
            )
            solution = candidate.published_solution_latex
            if (not include_solution or solution) and (
                not include_idea or candidate.idea_latex
            ):
                continue
            provisional.append(
                parent.model_copy(
                    update={
                        "ordinal": len(provisional) + 1,
                        "source_kind": SourceKind.COMPLETION,
                        "parent_spec_id": parent.spec_id,
                        "parent_problem_latex": candidate.published_problem_latex,
                        "parent_artifact_sha256": hashlib.sha256(
                            candidate.final_latex.encode()
                        ).hexdigest(),
                        "parent_idea_latex": candidate.idea_latex,
                        "parent_solution_latex": solution,
                        "parent_final_latex": candidate.final_latex,
                        "parent_was_accepted": row["status"] == "accepted",
                        "include_solution": bool(solution) or include_solution,
                        "include_idea": bool(candidate.idea_latex) or include_idea,
                        "variant_family": None,
                    }
                )
            )
    if not provisional:
        raise ValueError(
            "the selected problems already contain the requested components"
        )
    parent_ids = [spec.parent_spec_id for spec in provisional]
    request = parent_plan.request.model_copy(
        update={
            "count": len(provisional),
            "include_solution": include_solution,
            "include_idea": include_idea,
            "completion_parent_spec_ids": parent_ids,
            "variant_parent_spec_id": None,
        }
    )
    encoded = json.dumps(
        {
            "completion": [
                spec.model_dump(mode="json", exclude={"spec_id"})
                for spec in provisional
            ]
        },
        sort_keys=True,
    ).encode()
    plan_id = hashlib.sha256(encoded).hexdigest()
    specs = tuple(
        spec.model_copy(
            update={
                "spec_id": hashlib.sha256(
                    f"{plan_id}:{spec.parent_spec_id}".encode()
                ).hexdigest()
            }
        )
        for spec in provisional
    )
    return parent_plan.model_copy(
        update={
            "plan_id": plan_id,
            "request": request,
            "items": specs,
            "distributions": {
                "topic": dict(Counter(spec.topic_id for spec in specs)),
                "source_kind": {"completion": len(specs)},
            },
            "estimated_agent_calls": sum(
                7 if spec.include_solution else 1 for spec in specs
            ),
            "warnings": (
                "Adds only missing components to the same numbered files; existing questions, solutions, and ideas are preserved.",
            ),
        }
    )
