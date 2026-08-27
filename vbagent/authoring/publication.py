"""Publish numbered human files and assemble the project-root document."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vbagent.authoring.exports import (
    assert_regular_owned_path,
    atomic_bytes,
    digest,
    export_run_locked,
    exported_items,
    json_bytes,
    publication_lock,
)
from vbagent.authoring.paths import (
    generated_build_path,
    generated_output_root,
    publication_workspace_root,
)
from vbagent.authoring.store import AuthoringStore


def publication_stage(stats: dict[str, Any], publication: dict[str, Any]) -> str:
    """Use the same final stage for workers, rebuilds, and author decisions."""
    if publication.get("status") in {"failed", "compile_failed"}:
        return "completed_with_build_error"
    if stats.get("needs_review"):
        return "awaiting_author_review"
    return "drafts_ready" if stats.get("draft") else "completed"


def validate_problem_numbers(numbers: list[int] | None) -> list[int] | None:
    """Validate explicit human file selection without silently widening it."""
    if numbers is None:
        return None
    if (
        not isinstance(numbers, list) or not 1 <= len(numbers) <= 1000
        or any(type(number) is not int or number < 1 for number in numbers)
        or len(set(numbers)) != len(numbers)
    ):
        raise ValueError("problem_numbers must contain 1 to 1000 distinct positive integers")
    return list(numbers)


def assemble_generated_run(
    store: AuthoringStore,
    run_id: str,
    *,
    progress_callback: Callable[[str], None] | None = None,
    problem_numbers: list[int] | None = None,
) -> dict[str, Any]:
    """Reuse CLI assembly, answer extraction and PDF compilation.

    Numbered files accumulate across runs. Review copies are not compiled.
    Explicitly deferred-solution drafts are compiled with a visible warning.
    Unowned files and manual edits are never overwritten.
    """
    root = Path(store.get_run(run_id)["output_dir"])
    workspace = publication_workspace_root(root)
    generated = generated_output_root(root)
    build_path = generated_build_path(root, run_id)
    ownership_path = root / "publication.json"
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": "building",
        "problem_count": 0,
        "run_problem_count": 0,
        "problem_numbers": [],
        "requested_problem_numbers": problem_numbers,
        "draft_count": 0,
        "review_count": 0,
        "main_tex_path": None,
        "answer_key_path": None,
        "pdf_path": None,
        "compile_success": False,
        "error": None,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    def progress(stage: str) -> None:
        if progress_callback:
            progress_callback(stage)

    try:
        selection = validate_problem_numbers(problem_numbers)
        progress("publishing_outputs")
        with publication_lock(root):
            current = export_run_locked(store, run_id)
            all_items = exported_items(store, root)
            eligible = [
                item for item in all_items if item["status"] in {"accepted", "draft"}
            ]
            if selection is not None:
                by_number = {item["number"]: item for item in eligible}
                unavailable = [number for number in selection if number not in by_number]
                if unavailable:
                    raise ValueError(
                        f"requested problems are missing or not ready for publication: {unavailable}; "
                        "the existing root document was preserved"
                    )
                eligible = [by_number[number] for number in selection]
            selected_numbers = {item["number"] for item in eligible}
            payload.update(
                problem_count=len(eligible),
                problem_numbers=[item["number"] for item in eligible],
                run_problem_count=sum(
                    item.get("number") in selected_numbers for item in current
                ),
                draft_count=sum(item["status"] == "draft" for item in eligible),
                review_count=sum(item["status"] == "needs_review" for item in current),
            )
            manifest_path = generated / "manifest.json"
            assert_regular_owned_path(manifest_path, generated)
            if manifest_path.exists():
                previous = json.loads(manifest_path.read_text(encoding="utf-8"))
                if previous.get("kind") != "vbagent_generated_collection":
                    raise ValueError(f"unrelated manifest preserved: {manifest_path}")
            if not eligible:
                payload.update(
                    status="skipped",
                    error="no accepted problems or explicitly requested drafts are ready to assemble",
                )
            else:
                _assemble_owned_bundle(
                    store,
                    run_id,
                    root,
                    workspace,
                    generated,
                    eligible,
                    ownership_path,
                    payload,
                    progress,
                )
            manifest = {
                "schema_version": 1,
                "kind": "vbagent_generated_collection",
                "generated_output_dir": str(generated),
                "publication": payload,
                "artifacts": all_items,
            }
            atomic_bytes(manifest_path, json_bytes(manifest))
    except Exception as exc:
        payload.update(
            status="failed", compile_success=False, error=f"{type(exc).__name__}: {exc}"
        )
    payload["updated_at"] = datetime.now(UTC).isoformat()
    atomic_bytes(build_path, json_bytes(payload))
    return payload


def _assemble_owned_bundle(
    store, run_id, root, workspace, generated, items, ownership_path, payload, progress
):
    from vbagent.cli.compilation.compile_main import generate_main_tex
    from vbagent.cli.management.extans import _add_answer_key_to_main, _format_latex
    from vbagent.dpp.builder import DPPResult
    from vbagent.tex import extract_answer_details_from_problem

    workspace.mkdir(parents=True, exist_ok=True)
    paths = {
        name: workspace / name for name in ("main.tex", "answer_key.tex", "main.pdf")
    }
    assert_regular_owned_path(ownership_path, root)
    owned = (
        json.loads(ownership_path.read_text(encoding="utf-8"))
        if ownership_path.is_file()
        else {}
    )
    known_hashes = owned.get("managed_files", {})
    for name, path in paths.items():
        assert_regular_owned_path(path, workspace)
        if path.exists() and digest(path.read_bytes()) != known_hashes.get(name):
            raise ValueError(f"existing or manually edited file preserved: {path}")

    problem_paths = [Path(item["path"]) for item in items]
    for path, item in zip(problem_paths, items):
        assert_regular_owned_path(path, generated)
        if not path.is_file() or digest(path.read_bytes()) != item["content_sha256"]:
            raise ValueError(
                f"generated problem was edited or is missing; review before automatic assembly: {path}"
            )

    progress("assembling_sources")
    request = store.load_request(run_id)
    subjects = {item["specification"]["subject"] for item in items}
    title = (
        f"{request.exam.replace('_', ' ').upper()} {request.subject.title()} Problems"
        if len(subjects) == 1
        else "Generated Problems"
    )
    common = dict(
        scans_dir=str(generated),
        title=title,
        subject=request.subject,
        problem_list=[path.stem for path in problem_paths],
        use_foreach=True,
        include_all_packages=len(subjects) > 1,
    )
    root_main = generate_main_tex(output_file=str(paths["main.tex"]), **common)
    show_ideas = any(item["specification"].get("include_idea", True) for item in items)
    if show_ideas:
        root_main = root_main.replace(
            r"\excludecomment{idea}", r"% \excludecomment{idea}"
        )
    warning = (
        "\\par\\noindent\\textbf{Draft collection: some solutions and correctness checks are deferred.}\\par\n"
        if payload["draft_count"]
        else ""
    )
    if warning:
        root_main = root_main.replace("\\maketitle\n", "\\maketitle\n" + warning)

    progress("extracting_answer_key")
    answers, kinds = {}, {}
    for index, (path, item) in enumerate(zip(problem_paths, items), 1):
        answer = (
            extract_answer_details_from_problem(path) if item["validated"] else None
        )
        answers[index] = answer.value if answer else None
        kinds[index] = answer.kind if answer else None
    answer_content = (
        _format_latex(answers, kinds, max_columns=max(1, len(items))) + "\n"
    )
    if warning:
        answer_content = (
            "\\par\\noindent Unverified draft answers are intentionally omitted.\\par\n"
            + answer_content
        )

    with tempfile.TemporaryDirectory(prefix="vbagent_publication_") as temporary:
        staging = Path(temporary)
        staging_main = staging / "main.tex"
        staging_key = staging / "answer_key.tex"
        staged_content = generate_main_tex(output_file=str(staging_main), **common)
        if show_ideas:
            staged_content = staged_content.replace(
                r"\excludecomment{idea}", r"% \excludecomment{idea}"
            )
        if warning:
            staged_content = staged_content.replace(
                "\\maketitle\n", "\\maketitle\n" + warning
            )
        atomic_bytes(staging_main, staged_content.encode())
        atomic_bytes(staging_key, answer_content.encode())
        if _add_answer_key_to_main(staging_main, staging_key) not in {
            "added",
            "already_present",
        }:
            raise ValueError("could not include answer_key.tex")
        progress("compiling_bundle")
        success, result = DPPResult(
            questions=[],
            main_tex_path=staging_main,
            strategy_used="authoring-publication",
        ).compile(output_dir=staging, verbose=False)
        if not success:
            payload.update(status="compile_failed", error=str(result))
            return
        pdf_bytes = Path(result).read_bytes()

    with tempfile.TemporaryDirectory(prefix="vbagent_main_") as temporary:
        temp_main = Path(temporary) / "main.tex"
        temp_key = Path(temporary) / "answer_key.tex"
        atomic_bytes(temp_main, root_main.encode())
        atomic_bytes(temp_key, answer_content.encode())
        _add_answer_key_to_main(temp_main, temp_key)
        root_main = temp_main.read_text(encoding="utf-8")
    progress("publishing_outputs")
    contents = {
        "main.tex": root_main.encode(),
        "answer_key.tex": answer_content.encode(),
        "main.pdf": pdf_bytes,
    }
    for name, path in paths.items():
        assert_regular_owned_path(path, workspace)
        if path.exists() and digest(path.read_bytes()) != known_hashes.get(name):
            raise ValueError(f"file changed during compilation; preserved: {path}")
    for name, content in contents.items():
        atomic_bytes(paths[name], content, exclusive=not paths[name].exists())
    payload.update(
        status="completed",
        compile_success=True,
        main_tex_path=str(paths["main.tex"]),
        answer_key_path=str(paths["answer_key.tex"]),
        pdf_path=str(paths["main.pdf"]),
        error=None,
    )
    atomic_bytes(
        ownership_path,
        json_bytes(
            {
                "managed_files": {
                    name: digest(content) for name, content in contents.items()
                },
                "publication": payload,
            }
        ),
    )
