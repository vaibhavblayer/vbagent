"""Notes generator — orchestrates the full concept notes pipeline.

Pipeline: plan → sections (parallel) → diagrams (parallel) → stitch → compile
"""

from __future__ import annotations

import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from vbagent.agents.notes.models import (
    DocumentPlan, SectionContent, DiagramSpec, NotesResult,
)


def _collect_all_diagrams(plan: DocumentPlan) -> list[DiagramSpec]:
    """Collect all diagram specs from the plan."""
    diagrams = []
    for section in plan.sections:
        for sub in section.subsections:
            diagrams.extend(sub.diagrams)
    return diagrams


def generate_notes(
    topic: str,
    output_dir: str | Path = "agentic/notes",
    syllabus: str = "",
    subject: str = "physics",
    compile_pdf: bool = True,
    no_diagrams: bool = False,
    plan_only: bool = False,
    max_workers: int = 4,
    show_spinner: bool = True,
) -> NotesResult:
    """Generate complete concept notes for a topic.

    Args:
        topic: The topic to cover.
        output_dir: Output directory.
        syllabus: Optional syllabus text for scope guidance.
        subject: Subject (physics, chemistry, mathematics).
        compile_pdf: Whether to compile to PDF.
        no_diagrams: Skip diagram generation (use placeholders).
        plan_only: Only generate the plan, don't write content.
        max_workers: Max parallel workers for sections and diagrams.
        show_spinner: Show progress spinners.

    Returns:
        NotesResult with paths and metadata.
    """
    import json
    import re

    out_path = Path(output_dir)
    slug = re.sub(r'[^a-z0-9]+', '_', topic[:50].lower()).strip('_')
    notes_dir = out_path / slug
    notes_dir.mkdir(parents=True, exist_ok=True)
    diagrams_dir = notes_dir / "diagrams"
    diagrams_dir.mkdir(exist_ok=True)

    # ── Stage 1: Plan ────────────────────────────────────────────────
    from vbagent.agents.notes.planner import plan_notes

    plan = plan_notes(
        topic=topic,
        syllabus=syllabus,
        subject=subject,
        show_spinner=show_spinner,
    )

    # Save plan
    plan_path = notes_dir / "plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan.model_dump(), f, indent=2)

    if plan_only:
        return NotesResult(
            tex_path=str(plan_path),
            title=plan.title,
            sections=len(plan.sections),
            diagrams=sum(
                len(d) for s in plan.sections for sub in s.subsections for d in [sub.diagrams]
            ),
        )

    # ── Stage 2: Write sections (parallel) ───────────────────────────
    from vbagent.agents.notes.section_writer import write_section

    section_contents: dict[int, SectionContent] = {}
    section_errors: list[tuple[int, Exception]] = []

    def _write_one_section(idx, sec_plan):
        return idx, write_section(
            section_plan=sec_plan,
            section_index=idx,
            total_sections=len(plan.sections),
            topic=topic,
            subject=subject,
            show_spinner=False,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_write_one_section, i, sec): i
            for i, sec in enumerate(plan.sections)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                i, content = future.result()
                section_contents[i] = content
            except Exception as e:
                section_errors.append((idx, e))

    # Handle section errors
    for idx, err in section_errors:
        section_contents[idx] = SectionContent(
            section_title=plan.sections[idx].title,
            latex=f"\\section{{{plan.sections[idx].title}}}\n\n% ERROR: Section generation failed: {err}\n",
        )

    ordered_sections = [section_contents[i] for i in range(len(plan.sections))]

    # ── Stage 3: Generate diagrams (parallel) ────────────────────────
    all_diagrams = _collect_all_diagrams(plan)
    diagram_count = 0

    if not no_diagrams and all_diagrams:
        from vbagent.agents.notes.diagram_generator import generate_diagram

        def _gen_one_diagram(spec):
            return generate_diagram(
                spec=spec,
                output_dir=diagrams_dir,
                show_spinner=False,
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_gen_one_diagram, spec): spec
                for spec in all_diagrams
            }
            for future in as_completed(futures):
                spec = futures[future]
                try:
                    future.result()
                    diagram_count += 1
                except Exception as e:
                    # Write a placeholder for failed diagrams
                    placeholder = (
                        f"% Diagram generation failed: {e}\n"
                        f"% Description: {spec.description}\n"
                        f"\\begin{{center}}\\textit{{[Diagram: {spec.description[:80]}...]}}\\end{{center}}\n"
                    )
                    (diagrams_dir / f"{spec.diagram_id}.tex").write_text(
                        placeholder, encoding="utf-8"
                    )
    elif no_diagrams and all_diagrams:
        # Write placeholders for all diagrams
        for spec in all_diagrams:
            placeholder = (
                f"% Diagram skipped (--no-diagrams)\n"
                f"\\begin{{center}}\\textit{{[Diagram: {spec.caption}]}}\\end{{center}}\n"
            )
            (diagrams_dir / f"{spec.diagram_id}.tex").write_text(
                placeholder, encoding="utf-8"
            )

    # ── Stage 4: Stitch ──────────────────────────────────────────────
    from vbagent.agents.notes.stitcher import stitch_notes

    tex_path = notes_dir / f"{slug}.tex"
    stitch_notes(
        plan=plan,
        section_contents=ordered_sections,
        output_path=tex_path,
        diagrams_dir="diagrams",
    )

    # ── Stage 5: Compile (optional) ──────────────────────────────────
    pdf_path = None
    if compile_pdf:
        pdf_path = _compile_notes(tex_path, notes_dir)

    return NotesResult(
        tex_path=str(tex_path),
        pdf_path=pdf_path,
        title=plan.title,
        sections=len(plan.sections),
        diagrams=diagram_count,
    )


def _compile_notes(tex_path: Path, work_dir: Path) -> Optional[str]:
    """Compile a .tex file to PDF using pdflatex."""
    if not shutil.which("pdflatex"):
        return None

    # Run pdflatex twice (for TOC and references)
    for run in range(2):
        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                str(tex_path.name),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(work_dir),
        )
        if result.returncode != 0 and run == 0:
            # First run might fail on references, try second anyway
            continue
        elif result.returncode != 0 and run == 1:
            return None

    pdf_name = tex_path.stem + ".pdf"
    pdf_path = work_dir / pdf_name
    if pdf_path.exists():
        return str(pdf_path)
    return None
