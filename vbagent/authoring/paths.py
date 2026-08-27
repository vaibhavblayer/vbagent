"""Deterministic paths for durable authoring evidence and published outputs."""

from __future__ import annotations

import re
from pathlib import Path

from vbagent.authoring.models import GenerationSpec

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")


def generated_output_root(authoring_root: str | Path) -> Path:
    """Return the accepted-artifact root for one authoring workspace.

    The conventional ``agentic/authoring`` workspace publishes to its sibling
    ``agentic/generated`` directory. Custom workspaces remain self-contained
    under ``<workspace>/generated``.
    """
    root = Path(authoring_root).expanduser().resolve()
    if root.name.casefold() == "authoring":
        return root.parent / "generated"
    return root / "generated"


def generated_run_dir(authoring_root: str | Path, run_id: str) -> Path:
    """Return internal, run-bound publication reports, never the human folder."""
    _validate_component(run_id, "run ID")
    return Path(authoring_root).expanduser().resolve() / "runs" / run_id / "publication"


def publication_workspace_root(authoring_root: str | Path) -> Path:
    """Place the assembled document at the project root, not under agentic."""
    root = Path(authoring_root).expanduser().resolve()
    if root.name.casefold() == "authoring":
        return root.parent.parent if root.parent.name.casefold() == "agentic" else root.parent
    return root


def generated_problem_path(authoring_root: str | Path, number: int) -> Path:
    if number < 1:
        raise ValueError("problem number must be positive")
    return generated_output_root(authoring_root) / f"problem_{number}.tex"


def generated_collection_manifest_path(authoring_root: str | Path) -> Path:
    return generated_output_root(authoring_root) / "manifest.json"


def generated_artifact_path(
    authoring_root: str | Path,
    run_id: str,
    spec: GenerationSpec,
) -> Path:
    """Return the immutable internal accepted artifact (IDs are machine-only)."""
    return generated_artifact_path_for_item(
        authoring_root,
        run_id,
        ordinal=spec.ordinal,
        spec_id=spec.spec_id,
    )


def generated_artifact_path_for_item(
    authoring_root: str | Path,
    run_id: str,
    *,
    ordinal: int,
    spec_id: str,
) -> Path:
    """Return a published path without materializing a full generation spec."""
    if ordinal < 1:
        raise ValueError("artifact ordinal must be positive")
    _validate_component(spec_id, "spec ID")
    _validate_component(run_id, "run ID")
    return Path(authoring_root).expanduser().resolve() / "runs" / run_id / "accepted" / (
        f"problem_{ordinal:06d}_{spec_id[:12]}.tex"
    )


def generated_manifest_path(authoring_root: str | Path, run_id: str) -> Path:
    """Return the machine-readable manifest path for one published run."""
    return generated_run_dir(authoring_root, run_id) / "manifest.json"


def generated_build_path(authoring_root: str | Path, run_id: str) -> Path:
    """Return the derived main/answer/PDF build report path."""
    return generated_run_dir(authoring_root, run_id) / "build.json"


def _validate_component(value: str, label: str) -> None:
    if not value or not _SAFE_COMPONENT.fullmatch(value):
        raise ValueError(f"invalid {label} for generated artifact path")
