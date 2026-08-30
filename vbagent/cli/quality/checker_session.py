"""Reusable interactive checker-session workflow."""

from __future__ import annotations

import re
import signal
import sys
from pathlib import Path
from typing import Optional

from vbagent.cli.common import (
    _get_console,
    _get_panel,
    _get_syntax,
    _get_table,
    discover_tex_files,
    display_diff,
    find_image_for_problem,
    format_latex,
    has_diagram_placeholder,
    natural_sort_key,
    open_content_in_editor,
)
from vbagent.cli.quality.session_actions import prompt_checker_action
from vbagent.cli.quality.tikz_support import _generate_tikz_for_placeholder
from vbagent.models.diff import generate_diff


def _detect_subject_for_file(tex_file: Path) -> str:
    """Detect the subject for a .tex file from its classification JSON.

    Looks for agentic/classifications/{stem}.json next to the scans dir.
    Falls back to 'physics' if not found.
    """
    import json

    stem = tex_file.stem  # e.g. "problem_21"

    # Try sibling classifications/ directory
    for candidate_dir in [
        tex_file.parent.parent / "classifications",  # agentic/scans/../classifications
        tex_file.parent / "classifications",          # same dir
        Path("agentic") / "classifications",          # from cwd
    ]:
        json_path = candidate_dir / f"{stem}.json"
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text())
                return data.get("subject", "physics")
            except Exception:
                pass

    # Fallback: scan the tex file for % subject: comment
    try:
        for line in tex_file.read_text().split("\n")[:10]:
            if line.startswith("% subject:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass

    return "physics"


def _filter_tex_files_by_item_range(
    tex_files: list[Path],
    item_range: tuple[int, int] | None,
) -> list[Path]:
    """Select files by the last numeric component of their stem."""
    if item_range is None:
        return tex_files

    start, end = item_range
    selected: list[Path] = []
    for tex_file in tex_files:
        match = re.search(r"(\d+)(?!.*\d)", tex_file.stem)
        if match and start <= int(match.group(1)) <= end:
            selected.append(tex_file)
    return selected


def run_checker_session(
    output_dir: str,
    count: int | None,
    problem_id: Optional[str],
    checker_name: str,
    check_func_module: str,
    check_func_name: str,
    require_solution: bool = False,
    require_tikz: bool = False,
    reset: bool = False,
    images_dir: Optional[str] = None,
    extra_prompt: Optional[str] = None,
    auto_approve: bool = False,
    item_range: tuple[int, int] | None = None,
    check_kwargs: Optional[dict] = None,
    progress_key: str | None = None,
    skip_checked: bool = True,
) -> None:
    """Run an interactive checker session with approval workflow.

    Saves progress to database for tracking and potential resume.
    Skips already-checked files unless reset=True.

    Args:
        output_dir: Directory containing .tex files
        count: Number of files to process
        problem_id: Optional specific problem ID to check
        checker_name: Name of the checker (solution/grammar/clarity/tikz)
        check_func_module: Module containing the check function
        check_func_name: Name of the check function
        require_solution: Whether to require solution environment
        require_tikz: Whether to require TikZ code (for tikz checker)
        reset: Whether to reset progress and re-check all files
        images_dir: Optional directory containing images for problems
        extra_prompt: Optional additional instructions for the checker
        auto_approve: Whether to auto-approve all suggestions without prompting
        item_range: Optional inclusive numeric file range
        check_kwargs: Additional keyword arguments for the check function
        progress_key: Optional durable key distinct from the displayed checker name
        skip_checked: Reuse durable completion state when true
    """
    import importlib
    from vbagent.models.version_store import VersionStore, SuggestionStatus
    from vbagent.models.review import Suggestion, ReviewIssueType as IssueType

    # Dynamically import the check function
    module = importlib.import_module(check_func_module)
    check_func = getattr(module, check_func_name)

    # Import has_tikz_environment for tikz checker (needed for generation detection)
    has_tikz_environment = None
    if checker_name == "tikz" or require_tikz:
        from vbagent.agents.diagram.tikz_checker import has_tikz_environment

    console = _get_console()

    output_path = Path(output_dir)
    tex_files = discover_tex_files(output_path)

    if not tex_files:
        console.print(f"[red]Error:[/red] No .tex files found in {output_dir}")
        raise SystemExit(1)

    tex_files = sorted(tex_files, key=natural_sort_key)

    if problem_id:
        tex_files = [f for f in tex_files if problem_id in f.stem]
        if not tex_files:
            console.print(f"[red]Error:[/red] No files found matching '{problem_id}'")
            raise SystemExit(1)

    tex_files = _filter_tex_files_by_item_range(tex_files, item_range)
    if item_range is not None:
        start, end = item_range
        end_label = "end" if end == sys.maxsize else str(end)
        console.print(
            f"[cyan]Filtering to items {start}-{end_label}: "
            f"{len(tex_files)} file(s)[/cyan]"
        )
        if not tex_files:
            console.print("[red]Error:[/red] No files found in the selected range")
            raise SystemExit(1)

    # Filter for TikZ files if required
    if require_tikz and has_tikz_environment:
        tikz_files = []
        for f in tex_files:
            content = f.read_text()
            if has_tikz_environment(content):
                tikz_files.append(f)
        tex_files = tikz_files
        if not tex_files:
            console.print(f"[yellow]No files with TikZ code found in {output_dir}[/yellow]")
            return

    # Initialize version store for tracking
    store = VersionStore(base_dir=".")
    output_dir_normalized = str(output_path.resolve())
    tracking_name = progress_key or checker_name

    # Reset progress if requested
    if reset:
        reset_count = store.reset_checker_progress(tracking_name, output_dir_normalized)
        if reset_count > 0:
            console.print(f"[yellow]Reset progress for {reset_count} file(s)[/yellow]")

    # Filter out already-checked files
    checked_files = (
        store.get_checked_files(tracking_name, output_dir_normalized)
        if skip_checked
        else set()
    )
    unchecked_files = [f for f in tex_files if str(f.resolve()) not in checked_files]

    if skip_checked and not unchecked_files:
        console.print(f"[green]OK All {len(tex_files)} file(s) have already been checked for {checker_name} issues[/green]")
        stats = store.get_checker_stats(tracking_name, output_dir_normalized)
        console.print(f"[dim]Total: {stats['total']}, Passed: {stats['passed']}, Had issues: {stats['failed']}[/dim]")
        console.print("[dim]Use --reset to re-check files[/dim]")
        store.close()
        return

    if len(checked_files) > 0:
        console.print(f"[dim]Skipping {len(checked_files)} already-checked file(s)[/dim]")

    to_process = unchecked_files if count is None else unchecked_files[:count]
    console.print(f"[cyan]Checking {len(to_process)} file(s) for {checker_name} issues[/cyan]")
    session_id = store.create_session()

    # Map checker names to issue types
    issue_type_map = {
        "solution": IssueType.PHYSICS_ERROR,
        "grammar": IssueType.GRAMMAR,
        "clarity": IssueType.CLARITY,
        "edit": IssueType.CLARITY,
        "tikz": IssueType.FORMATTING,
    }
    issue_type = issue_type_map.get(checker_name, IssueType.OTHER)

    stats = {
        "processed": 0,
        "passed": 0,
        "approved": 0,
        "rejected": 0,
        "skipped": 0,
        "session_id": session_id,
    }

    shutdown_requested = False

    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        shutdown_requested = True
        console.print("\n[yellow]Shutdown requested. Saving progress...[/yellow]")

    original_sigint = signal.signal(signal.SIGINT, signal_handler)
    # SIGTERM is not available on Windows
    original_sigterm = None
    if sys.platform != "win32":
        original_sigterm = signal.signal(signal.SIGTERM, signal_handler)

    try:
        for idx, tex_file in enumerate(to_process):
            if shutdown_requested:
                break

            rel_path = tex_file.relative_to(output_path) if output_path.is_dir() else tex_file.name
            problem_name = tex_file.stem
            console.print(f"\n[bold cyan]═══ [{idx+1}/{len(to_process)}] {rel_path} ═══[/bold cyan]")

            content = tex_file.read_text()

            # Find corresponding image
            # 1. Use explicit images_dir if provided
            # 2. For tikz checker, auto-discover if file has \input{diagram} placeholder
            image_path = None
            if images_dir:
                image_path = find_image_for_problem(tex_file, images_dir)
                if image_path:
                    console.print(f"[dim]Image: {image_path.name}[/dim]")
            elif checker_name == "tikz":
                # Auto-discover image if file has diagram placeholder
                if has_diagram_placeholder(content):
                    image_path = find_image_for_problem(tex_file, auto_discover=True)
                    if image_path:
                        console.print(f"[dim]Auto-found image: {image_path.name}[/dim]")

            # For tikz checker: check if generation is needed (has placeholder but no TikZ)
            if checker_name == "tikz" and has_tikz_environment:
                needs_generation = has_diagram_placeholder(content) and not has_tikz_environment(content)

                if needs_generation:
                    # Generate TikZ instead of checking
                    console.print("[cyan]Generating TikZ (found \\input{diagram} placeholder)[/cyan]")

                    if not image_path:
                        console.print("[yellow]Warning: No image found for generation. Results may be limited.[/yellow]")

                    try:
                        generated_content = _generate_tikz_for_placeholder(
                            content=content,
                            image_path=image_path,
                            diagram_type=None,
                            extra_prompt=extra_prompt,
                            console=console,
                        )
                        stats["processed"] += 1

                        if not generated_content:
                            console.print("[yellow]Failed to generate TikZ[/yellow]")
                            stats["skipped"] += 1
                            continue

                        # Show the generated content
                        diff_text = generate_diff(content, generated_content, str(rel_path))

                        if diff_text:
                            console.print("\n[bold]Generated TikZ:[/bold]")
                            display_diff(diff_text, console)

                        # Create suggestion for tracking
                        suggestion = Suggestion(
                            file_path=str(tex_file),
                            issue_type=issue_type,
                            description="TikZ generation: replaced \\input{diagram} placeholder",
                            original_content=content,
                            suggested_content=generated_content,
                            diff=diff_text,
                            reasoning="Generated TikZ code from image to replace placeholder.",
                            confidence=0.8,
                        )

                        # Prompt for action
                        action = "approve" if auto_approve else prompt_checker_action(console)
                        if auto_approve:
                            console.print("[dim]Auto-approving...[/dim]")

                        if action == "quit":
                            shutdown_requested = True
                            break
                        elif action == "skip":
                            console.print("[dim]Skipped[/dim]")
                            stats["skipped"] += 1
                            continue
                        elif action == "reject":
                            store.save_suggestion(suggestion, problem_name, SuggestionStatus.REJECTED, session_id)
                            store.mark_file_checked(str(tex_file.resolve()), tracking_name, output_dir_normalized, passed=False)
                            console.print("[yellow]Suggestion stored for later[/yellow]")
                            stats["rejected"] += 1
                            continue

                        final_content = generated_content
                        if action == "edit":
                            success, edited = open_content_in_editor(str(tex_file), generated_content, console)
                            if success and edited:
                                final_content = edited
                                console.print("[cyan]Content edited[/cyan]")

                        # Write the generated content
                        try:
                            tex_file.write_text(final_content)
                            console.print(f"[green]OK TikZ generated and applied to {rel_path}[/green]")
                            store.save_suggestion(suggestion, problem_name, SuggestionStatus.APPROVED, session_id)
                            store.mark_file_checked(str(tex_file.resolve()), tracking_name, output_dir_normalized, passed=False)
                            stats["approved"] += 1
                        except (IOError, OSError) as e:
                            console.print(f"[red]ERROR Failed to write: {e}[/red]")
                            stats["rejected"] += 1

                        continue

                    except KeyboardInterrupt:
                        console.print("\n[yellow]Interrupted[/yellow]")
                        shutdown_requested = True
                        break
                    except Exception as e:
                        console.print(f"[red]Error generating TikZ:[/red] {e}")
                        stats["skipped"] += 1
                        continue

            if require_solution and r'\begin{solution}' not in content:
                console.print("[yellow]No solution environment found, skipping[/yellow]")
                stats["skipped"] += 1
                continue

            # For tikz checker: skip files without TikZ content (unless it needs generation)
            if checker_name == "tikz" and has_tikz_environment:
                has_tikz = has_tikz_environment(content)
                has_placeholder = has_diagram_placeholder(content)

                if not has_tikz and not has_placeholder:
                    console.print("[dim]No TikZ content found, skipping[/dim]")
                    stats["skipped"] += 1
                    # Mark as checked/passed since there's nothing to check
                    store.mark_file_checked(str(tex_file.resolve()), tracking_name, output_dir_normalized, passed=True)
                    continue

            # Prepare content with extra prompt if provided
            check_content = content
            if extra_prompt:
                console.print(f"[dim]Extra instructions: {extra_prompt}[/dim]")
                if checker_name != "edit":
                    # Legacy checkers receive extra instructions as context.
                    check_content = (
                        f"% ADDITIONAL INSTRUCTIONS: {extra_prompt}\n\n{content}"
                    )

            try:
                console.print(f"[dim]Checking {checker_name}... (Ctrl+C to quit)[/dim]")
                # Pass image to tikz checker if available
                if checker_name == "tikz" and image_path:
                    passed, summary, corrected_content = check_func(check_content, image_path=str(image_path))
                elif checker_name == "format":
                    # Detect subject from classification JSON for subject-aware formatting
                    subject = _detect_subject_for_file(tex_file)
                    if subject and subject != "physics":
                        console.print(f"[dim]Subject: {subject}[/dim]")
                    passed, summary, corrected_content = check_func(check_content, subject=subject)
                elif checker_name == "edit":
                    passed, summary, corrected_content = check_func(
                        content,
                        instruction=extra_prompt or "",
                        **(check_kwargs or {}),
                    )
                else:
                    passed, summary, corrected_content = check_func(check_content)
                stats["processed"] += 1
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
                shutdown_requested = True
                break
            except Exception as e:
                console.print(f"[red]Error checking {checker_name}:[/red] {e}")
                stats["skipped"] += 1
                continue

            if passed:
                console.print(f"[green]OK {summary}[/green]")
                stats["passed"] += 1
                # Mark file as checked (passed)
                store.mark_file_checked(str(tex_file.resolve()), tracking_name, output_dir_normalized, passed=True)
                continue

            # Clean up extra prompt from corrected content if it was added
            if (
                checker_name != "edit"
                and extra_prompt
                and corrected_content.startswith("% ADDITIONAL INSTRUCTIONS:")
            ):
                # Remove the extra instructions line
                lines = corrected_content.split('\n')
                # Skip the instruction line and any following blank lines
                start_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith("% ADDITIONAL INSTRUCTIONS:"):
                        start_idx = i + 1
                        # Skip blank lines after the instruction
                        while start_idx < len(lines) and not lines[start_idx].strip():
                            start_idx += 1
                        break
                corrected_content = '\n'.join(lines[start_idx:])

            # Show the summary
            console.print(f"[yellow]Issues found: {summary}[/yellow]")

            # Generate diff
            diff_text = generate_diff(content, corrected_content, str(rel_path))

            # Create suggestion object for database storage
            suggestion = Suggestion(
                file_path=str(tex_file),
                issue_type=issue_type,
                description=f"{checker_name.title()} check: {summary}",
                original_content=content,
                suggested_content=corrected_content,
                diff=diff_text,
                reasoning=f"Automated {checker_name} check found issues.",
                confidence=0.8,
            )

            if diff_text:
                console.print("\n[bold]Proposed Changes:[/bold]")
                display_diff(diff_text, console)
            else:
                # Fallback to showing corrected content if diff fails
                formatted_content = format_latex(corrected_content)
                syntax = _get_syntax(formatted_content, "latex", theme="monokai", line_numbers=False)
                console.print(_get_panel(
                    syntax,
                    title="[cyan]Corrected Content[/cyan]",
                    border_style="cyan"
                ))

            # Prompt for action
            if auto_approve:
                action = "approve"
                console.print("[dim]Auto-approving...[/dim]")
            else:
                action = prompt_checker_action(console)

            if action == "quit":
                shutdown_requested = True
                break

            if action == "skip":
                console.print("[dim]Skipped[/dim]")
                stats["skipped"] += 1
                continue

            if action == "reject":
                # Store for later without applying
                store.save_suggestion(
                    suggestion, problem_name,
                    SuggestionStatus.REJECTED, session_id
                )
                # Mark file as checked (had issues, rejected)
                store.mark_file_checked(str(tex_file.resolve()), tracking_name, output_dir_normalized, passed=False)
                console.print("[yellow]Suggestion stored for later[/yellow]")
                stats["rejected"] += 1
                continue

            final_content = corrected_content

            if action == "edit":
                success, edited = open_content_in_editor(
                    str(tex_file),
                    corrected_content,
                    console
                )
                if success and edited:
                    final_content = edited
                    console.print("[cyan]Content edited[/cyan]")
                else:
                    console.print("[yellow]Edit cancelled, using original correction[/yellow]")

            # Write the corrected content
            try:
                tex_file.write_text(final_content)
                console.print(f"[green]OK Corrections applied to {rel_path}[/green]")
                # Save as approved
                store.save_suggestion(
                    suggestion, problem_name,
                    SuggestionStatus.APPROVED, session_id
                )
                # Mark file as checked (had issues, approved fix)
                store.mark_file_checked(str(tex_file.resolve()), tracking_name, output_dir_normalized, passed=False)
                stats["approved"] += 1
            except (IOError, OSError) as e:
                console.print(f"[red]ERROR Failed to write: {e}[/red]")
                # Store as rejected since we couldn't apply
                store.save_suggestion(
                    suggestion, problem_name,
                    SuggestionStatus.REJECTED, session_id
                )
                # Mark file as checked (had issues, failed to apply)
                store.mark_file_checked(str(tex_file.resolve()), tracking_name, output_dir_normalized, passed=False)
                stats["rejected"] += 1

        # Update session with final stats
        store.update_session(
            session_id,
            problems_reviewed=stats["processed"],
            suggestions_made=stats["approved"] + stats["rejected"],
            approved_count=stats["approved"],
            rejected_count=stats["rejected"],
            skipped_count=stats["skipped"],
            completed=not shutdown_requested,
        )

    finally:
        signal.signal(signal.SIGINT, original_sigint)
        if original_sigterm is not None:
            signal.signal(signal.SIGTERM, original_sigterm)
        store.close()

    # Summary
    console.print("\n[bold]═══ Session Summary ═══[/bold]")
    table = _get_table(show_header=False, style="minimal")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Files checked", str(stats["processed"]))
    table.add_row("Passed", f"[green]{stats['passed']}[/green]")
    table.add_row("Approved", f"[green]{stats['approved']}[/green]")
    table.add_row("Rejected", f"[red]{stats['rejected']}[/red]")
    table.add_row("Skipped", f"[yellow]{stats['skipped']}[/yellow]")

    console.print(table)

    if shutdown_requested:
        console.print(f"\n[dim]Session {session_id[:8]} saved. View with: vbagent check history[/dim]")
