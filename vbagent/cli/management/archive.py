"""Archive command — export scans as structured ZIP for platform upload.

Two subcommands:
  vbagent archive pyq      — PYQ bulk upload (per-problem folders)
  vbagent archive product   — Product upload (standard + premium tiers)

Both share core utilities: tex parsing, PDF compilation, metadata assembly.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Optional

import click

from vbagent.cli.common import _get_console

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


# ===================================================================
# Shared utilities
# ===================================================================

def _get_preamble(subject: str) -> str:
    """Build a tight-crop preamble — 7in wide, 5mm margins, no page numbers."""
    from vbagent.cli.compilation.compile_main import generate_preamble
    preamble = generate_preamble(subject=subject, title="", include_all=True)
    preamble = re.sub(
        r"\\geometry\{[^}]*\}",
        r"\\geometry{paperwidth=7in, paperheight=50in, margin=5mm, noheadfoot}",
        preamble,
    )
    return preamble


def _wrap_part(preamble: str, body: str, part_type: str = "question") -> str:
    """Wrap a LaTeX snippet in a full compilable document."""
    doc = preamble + "\n\\pagestyle{empty}\n\\begin{document}\n"
    if part_type in ("question", "combined"):
        doc += "\\begin{enumerate}[leftmargin=*]\n" + body.strip() + "\n\\end{enumerate}\n"
    else:
        doc += body.strip() + "\n"
    doc += "\\end{document}\n"
    return doc


def _compile_to_svg(tex_content: str, output_svg: Path, console=None) -> bool:
    """Compile LaTeX string to SVG via latex + dvisvgm."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "doc.tex").write_text(tex_content, encoding='utf-8')
        try:
            # Step 1: latex → DVI
            subprocess.run(
                ["latex", "-interaction=nonstopmode", "-halt-on-error", "doc.tex"],
                cwd=tmpdir, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30,
            )
            dvi = tmp / "doc.dvi"
            if not dvi.exists():
                if console:
                    log_file = tmp / "doc.log"
                    if log_file.exists():
                        log = log_file.read_text(encoding='utf-8', errors='replace')
                        errs = [l for l in log.split("\n") if l.startswith("!")][:3]
                        if errs:
                            console.print(f"[dim red]  {'  '.join(errs)}[/dim red]")
                return False
            
            # Step 2: dvisvgm → SVG (with tight bounding box)
            subprocess.run(
                ["dvisvgm", "--bbox=min", "--optimize", "--exact", "doc.dvi", "-o", "doc.svg"],
                cwd=tmpdir, capture_output=True, encoding='utf-8', errors='replace', timeout=15,
            )
            svg = tmp / "doc.svg"
            if not svg.exists():
                if console:
                    console.print(f"[dim red]  dvisvgm failed to generate SVG[/dim red]")
                return False
            
            shutil.copy2(svg, output_svg)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            if console:
                console.print(f"[red]  compile error: {e}[/red]")
            return False


def _parse_tex(content: str) -> dict[str, str]:
    """Split a scan .tex file into named parts.
    
    For question.svg: removes \\ans markers but keeps all options.
    For combined.svg: keeps everything including \\ans markers.
    Handles multiple alternatesolution blocks (alternate-1, alternate-2, etc.)
    """
    parts: dict[str, str] = {"combined": content.strip()}
    sol = re.search(r"(\\begin\{solution\}.*?\\end\{solution\})", content, re.DOTALL)
    if sol:
        parts["solution"] = sol.group(1)
    idea = re.search(r"(\\begin\{idea\}.*?\\end\{idea\})", content, re.DOTALL)
    if idea:
        parts["idea"] = idea.group(1)
    
    # Extract all alternatesolution blocks (can be multiple)
    alt_matches = list(re.finditer(r"(\\begin\{alternatesolution\}.*?\\end\{alternatesolution\})", content, re.DOTALL))
    if alt_matches:
        for idx, match in enumerate(alt_matches, start=1):
            parts[f"alternate-{idx}"] = match.group(1)
    
    # Question = everything before first environment
    first = None
    for env in [r"\begin{solution}", r"\begin{idea}", r"\begin{alternatesolution}"]:
        idx = content.find(env)
        if idx != -1 and (first is None or idx < first):
            first = idx
    
    question_content = content[:first].strip() if first else content.strip()
    
    # For question.svg: remove \ans markers but keep all options
    question_without_ans = re.sub(r"\\ans\b", "", question_content)
    parts["question"] = question_without_ans.strip()
    
    return parts


def _load_classification(scans_dir: Path, stem: str) -> dict:
    """Load classification JSON for a problem."""
    cls_path = scans_dir.parent / "classifications" / f"{stem}.json"
    if cls_path.exists():
        try:
            return json.loads(cls_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _extract_topics(classification: dict, tex_content: str, scans_dir: Path = None, stem: str = "") -> list[str]:
    """Assemble topics array from structured sources (no regex on LaTeX).

    Priority:
    1. Classification JSON: topic, key_concepts
    2. Ideas JSON (agentic/ideas/problem_N.json): concepts, techniques
    3. Fallback: chapter name
    """
    topics: list[str] = []

    # 1. Classification data
    if classification.get("topic"):
        topics.append(classification["topic"])
    for kc in classification.get("key_concepts", []):
        if kc and kc.lower() not in [t.lower() for t in topics]:
            topics.append(kc)

    # 2. Ideas JSON (structured, clean)
    if scans_dir and stem:
        ideas_path = scans_dir.parent / "ideas" / f"{stem}.json"
        if ideas_path.exists():
            try:
                ideas_data = json.loads(ideas_path.read_text())
                for concept in ideas_data.get("concepts", []):
                    if concept and concept.lower() not in [t.lower() for t in topics]:
                        topics.append(concept)
                for technique in ideas_data.get("techniques", []):
                    if technique and technique.lower() not in [t.lower() for t in topics]:
                        topics.append(technique)
            except (json.JSONDecodeError, OSError):
                pass

    return [t.lower().strip() for t in topics if t and t.lower() != "none"]


def _extract_mcq_correct_option(tex_content: str) -> Optional[str]:
    """Extract the correct MCQ option letter from \\ans marker.
    
    Returns:
        Single letter (A, B, C, D) or comma-separated for multiple correct (A,C)
        None if not an MCQ or no answer found
    """
    # Find tasks environment
    tasks_match = re.search(r"\\begin\{tasks\}.*?\\end\{tasks\}", tex_content, re.DOTALL)
    if not tasks_match:
        return None
    
    tasks_content = tasks_match.group(0)
    
    # Find all \task positions and \ans positions
    task_positions = [(m.start(), 'task') for m in re.finditer(r'\\task\b', tasks_content)]
    ans_positions = [(m.start(), 'ans') for m in re.finditer(r'\\ans\b', tasks_content)]
    
    if not ans_positions:
        return None
    
    # Sort all markers by position
    all_markers = sorted(task_positions + ans_positions, key=lambda x: x[0])
    
    correct_options: list[str] = []
    task_count = 0
    
    # Track which tasks have \ans immediately after them
    for i, (pos, marker_type) in enumerate(all_markers):
        if marker_type == 'task':
            task_count += 1
            # Check if next marker is \ans
            if i + 1 < len(all_markers) and all_markers[i + 1][1] == 'ans':
                correct_options.append(chr(65 + task_count - 1))  # A=65, B=66, etc.
    
    if correct_options:
        return ','.join(correct_options)
    
    return None


def _natural_sort_key(path: Path):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", path.stem)]


def _human_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _discover_tex_files(scans_dir: Path, from_num=None, to_num=None) -> list[Path]:
    """Discover and filter .tex files."""
    files = sorted(scans_dir.glob("*.tex"), key=_natural_sort_key)
    if from_num or to_num:
        def _num(p):
            m = re.search(r"(\d+)", p.stem)
            return int(m.group(1)) if m else None
        files = [f for f in files if (n := _num(f)) is not None
                 and (from_num is None or n >= from_num)
                 and (to_num is None or n <= to_num)]
    return files


def _render_parts(tex_file: Path, preamble: str, out_dir: Path, console=None) -> dict[str, bool]:
    """Parse tex, compile each part to SVG. Returns {part_name: success}."""
    content = tex_file.read_text()
    # Strip metadata comments
    content_clean = "\n".join(
        l for l in content.split("\n")
        if not (l.strip().startswith("%") and re.match(r"%\s*\w+\s*:", l.strip()))
    )
    parts = _parse_tex(content_clean)

    # Check for alternate in separate alternates/ directory
    # This adds to any alternates already found in the main file
    alt_file = tex_file.parent.parent / "alternates" / f"{tex_file.stem}.tex"
    if alt_file.exists():
        alt_content = alt_file.read_text().strip()
        if alt_content:
            # Find the next available alternate number
            existing_alts = [k for k in parts.keys() if k.startswith("alternate-")]
            next_num = len(existing_alts) + 1
            parts[f"alternate-{next_num}"] = alt_content

    results: dict[str, bool] = {}
    for name, body in parts.items():
        if not body.strip():
            continue
        tex_doc = _wrap_part(preamble, body, part_type=name)
        # All parts use their name directly as the SVG filename
        svg_name = f"{name}.svg"
        ok = _compile_to_svg(tex_doc, out_dir / svg_name, console=console)
        results[name] = ok
    return results


# ===================================================================
# PYQ subcommand
# ===================================================================

def _extract_exam_metadata(image_path: Path, cache_dir: Path = None) -> dict:
    """Extract exam name and year from a PYQ image via lightweight LLM call.

    Results are cached to ``{cache_dir}/{stem}_exam.json`` so re-runs
    skip the LLM call.
    """
    # Check cache first
    stem = image_path.stem
    if cache_dir:
        cache_file = cache_dir / f"{stem}_exam.json"
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text())
                if cached.get("exam") or cached.get("year"):
                    return cached
            except (json.JSONDecodeError, OSError):
                pass

    from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
    from pydantic import BaseModel, Field

    class ExamMeta(BaseModel):
        exam: Optional[str] = Field(None, description="Exam: neet, jee, jee_advanced, or null")
        year: Optional[int] = Field(None, description="Year (e.g. 2024), or null")

    agent = create_agent(
        name="ExamMetaExtractor",
        instructions="Extract the exam name and year from the question image header/footer. Return JSON only.",
        output_type=ExamMeta,
        agent_type="classifier",
    )
    msg = create_image_message(str(image_path), "What exam and year is this question from?")
    try:
        result = run_agent_sync(agent, msg, show_spinner=False, timeout=15)
        data = {"exam": result.exam, "year": result.year}
        # Cache the result
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{stem}_exam.json"
            cache_file.write_text(json.dumps(data))
        return data
    except Exception:
        return {}


def _build_pyq_metadata(
    prob_num: int, classification: dict, tex_content: str,
    cli: dict, image_meta: dict,
    scans_dir: Path = None, stem: str = "",
) -> dict:
    """Build PYQ metadata.json matching the platform schema."""
    subject = cli.get("subject") or classification.get("subject", "physics")
    exam = cli.get("exam") or image_meta.get("exam") or "jee"
    year = cli.get("year") or image_meta.get("year") or 2024
    chapter = cli.get("chapter") or classification.get("chapter") or ""
    topics = _extract_topics(classification, tex_content, scans_dir, stem)
    if not topics and chapter:
        topics = [chapter.lower()]
    diff_raw = cli.get("difficulty") or classification.get("difficulty_score") or 5
    try:
        difficulty = int(diff_raw)
    except (ValueError, TypeError):
        difficulty = 5
    difficulty = max(1, min(difficulty, 10))
    problem_type = classification.get("question_type", "mcq_sc")
    
    # Extract correct MCQ option
    mcq_correct_option = _extract_mcq_correct_option(tex_content)

    metadata = {
        "subject": subject,
        "exam": exam,
        "year": int(year),
        "chapter": chapter.lower() if chapter else "",
        "topics": topics,
        "difficulty": difficulty,
        "problem_type": problem_type,
    }
    
    # Add mcq_correct_option only if it's an MCQ
    if mcq_correct_option and problem_type.startswith("mcq"):
        metadata["mcq_correct_option"] = mcq_correct_option
    
    return metadata


@click.command("pyq", context_settings=CONTEXT_SETTINGS)
@click.argument("scans_dir", type=click.Path(exists=True), default="agentic/scans")
@click.option("--output", "-o", default="archive", help="Output directory")
@click.option("--subject", "-s", type=click.Choice(["physics", "chemistry", "mathematics"]))
@click.option("--exam", "-e", type=click.Choice(["jee", "neet", "jee_advanced"]), default=None)
@click.option("--year", "-y", type=int)
@click.option("--chapter", "-c", default="", help="Chapter name")
@click.option("--difficulty", "-d", type=int, help="Difficulty 1-10")
@click.option("--images-dir", default=None, help="Directory with original images (for exam/year extraction)")
@click.option("--zip/--no-zip", "make_zip", default=True)
@click.option("--from", "from_num", type=int, default=None)
@click.option("--to", "to_num", type=int, default=None)
def pyq(scans_dir, output, subject, exam, year, chapter, difficulty, images_dir, make_zip, from_num, to_num):
    """Export scans as PYQ bulk upload ZIP.

    \b
    Output structure per problem:
    - problem-N/
      ├── combined.svg          (full problem with options and \\ans markers)
      ├── question.svg          (question with options, \\ans markers removed)
      ├── solution.svg
      ├── idea.svg              (optional)
      └── metadata.json         (includes mcq_correct_option for MCQs)
    
    \b
    Examples:
        vbagent archive pyq --exam neet --year 2024 --chapter "atoms and nuclei"
        vbagent archive pyq --from 1 --to 30
        vbagent archive pyq --images-dir images/   # auto-detect exam/year from images
    """
    console = _get_console()
    scans_path = Path(scans_dir)
    output_path = Path(output)
    tex_files = _discover_tex_files(scans_path, from_num, to_num)
    if not tex_files:
        console.print(f"[red]No .tex files in {scans_dir}[/red]")
        return

    if not subject:
        from vbagent.config import get_config
        subject = get_config().subject

    cli_overrides = {}
    if subject: cli_overrides["subject"] = subject
    if exam: cli_overrides["exam"] = exam
    if year: cli_overrides["year"] = year
    if chapter: cli_overrides["chapter"] = chapter
    if difficulty: cli_overrides["difficulty"] = difficulty

    # Resolve images directory
    img_dir = Path(images_dir) if images_dir else scans_path.parent / "images"

    preamble = _get_preamble(subject)
    console.print(f"[cyan]Archiving {len(tex_files)} PYQs → {output_path}/[/cyan]")
    ok_count, fail_count = 0, 0

    for tex_file in tex_files:
        num_match = re.search(r"(\d+)", tex_file.stem)
        prob_num = int(num_match.group(1)) if num_match else 0
        prob_dir = output_path / f"problem-{prob_num}"
        prob_dir.mkdir(parents=True, exist_ok=True)

        classification = _load_classification(scans_path, tex_file.stem)
        content = tex_file.read_text()

        # Auto-detect exam/year from image if not provided via CLI
        image_meta = {}
        if not exam or not year:
            # Try multiple common image locations
            candidates = [
                img_dir / f"{tex_file.stem}.png",
                img_dir / f"{tex_file.stem}.jpg",
                img_dir / f"{tex_file.stem}.jpeg",
                scans_path.parent.parent / "images" / f"{tex_file.stem}.png",
                scans_path.parent.parent / "images" / f"{tex_file.stem}.jpg",
                Path("images") / f"{tex_file.stem}.png",
                Path("images") / f"{tex_file.stem}.jpg",
            ]
            img_path = next((p for p in candidates if p.exists()), None)
            if img_path:
                console.print(f"  [dim]Extracting exam/year from {img_path.name}...[/dim]")
                cls_dir = scans_path.parent / "classifications"
                image_meta = _extract_exam_metadata(img_path, cache_dir=cls_dir)
            else:
                console.print(f"  [dim yellow]⚠ No image found for {tex_file.stem} — using defaults for exam/year[/dim yellow]")

        meta = _build_pyq_metadata(prob_num, classification, content, cli_overrides, image_meta,
                                    scans_dir=scans_path, stem=tex_file.stem)
        (prob_dir / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

        results = _render_parts(tex_file, preamble, prob_dir, console)
        rendered = [k for k, v in results.items() if v]
        failed = [k for k, v in results.items() if not v]

        if failed:
            fail_count += 1
            console.print(f"  [yellow]⚠[/yellow] problem-{prob_num} [dim]({', '.join(rendered)})[/dim] [yellow]✗ {', '.join(failed)}[/yellow]")
        else:
            ok_count += 1
            console.print(f"  [green]✓[/green] problem-{prob_num} [dim]({', '.join(rendered)})[/dim]")

    if make_zip and output_path.exists():
        zip_path = output_path.parent / f"{output_path.name}.zip"
        shutil.make_archive(str(output_path), "zip", str(output_path.parent), output_path.name)
        console.print(f"\n[green]✓[/green] {zip_path} ({_human_size(zip_path)})")
    elif output_path.exists():
        console.print(f"\n[dim]To create a zip file, run:[/dim]")
        console.print(f"[dim]  cd {output_path.parent} && zip -r {output_path.name}.zip {output_path.name}[/dim]")

    console.print(f"\n[cyan]Done:[/cyan] {ok_count} ok, {fail_count} with errors")


# ===================================================================
# Product subcommand
# ===================================================================

def _generate_description_md(metadata: dict) -> str:
    """Generate product description.md via LLM."""
    from vbagent.agents.base import create_agent, run_agent_sync

    prompt = f"""Write a compelling product description in Markdown for an educational problem set.

Product info:
- Title: {metadata.get('title', '')}
- Subject: {metadata.get('subject', '')}
- Exam: {metadata.get('exam', '')}
- Chapters: {', '.join(metadata.get('chapters', []))}
- Topics: {', '.join(metadata.get('topics', []))}
- Difficulty range: {metadata.get('difficulty_range', [1, 10])}
- Problem count: {metadata.get('problem_count', 0)}

Write 150-250 words. Include:
- What the set covers (topics, concepts)
- Who it's for (exam prep level)
- What makes it valuable (step-by-step solutions, idea blocks)
- Difficulty progression

Use markdown headers (##), bullet points, and bold for emphasis.
Do NOT include pricing or purchase info. Output ONLY the markdown."""

    agent = create_agent(
        name="ProductDescriptionWriter",
        instructions="You write concise, compelling educational product descriptions in Markdown.",
        agent_type="classifier",  # lightweight model
    )
    try:
        return run_agent_sync(agent, [{"role": "user", "content": prompt}], show_spinner=True, timeout=30)
    except Exception:
        # Fallback template
        title = metadata.get("title", "Problem Set")
        chapters = ", ".join(metadata.get("chapters", []))
        return f"## {title}\n\nA curated set of {metadata.get('problem_count', 0)} problems covering {chapters}.\n"


def _generate_thumbnail(tikz_dir: Path, output_png: Path, preamble: str, console=None) -> bool:
    """Generate thumbnail.png from the first TikZ diagram found."""
    tikz_files = sorted(tikz_dir.glob("*.tex"), key=_natural_sort_key) if tikz_dir.exists() else []
    if not tikz_files:
        return False

    tikz_code = tikz_files[0].read_text().strip()
    if not tikz_code:
        return False

    # Wrap in standalone square document
    doc = r"""\documentclass[border=10mm]{standalone}
\usepackage{tikz, circuitikz, pgfplots, amsmath, amssymb}
\usetikzlibrary{arrows.meta, patterns, calc, decorations.markings}
\pgfplotsset{compat=1.18}
\begin{document}
""" + tikz_code + "\n\\end{document}\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "thumb.tex").write_text(doc)
        try:
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "thumb.tex"],
                cwd=tmpdir, capture_output=True, timeout=20,
            )
            pdf = tmp / "thumb.pdf"
            if not pdf.exists():
                return False
            # PDF → PNG via pdftoppm
            subprocess.run(
                ["pdftoppm", "-png", "-r", "300", "-singlefile", str(pdf), str(tmp / "thumb")],
                cwd=tmpdir, capture_output=True, timeout=10,
            )
            png = tmp / "thumb.png"
            if png.exists():
                shutil.copy2(png, output_png)
                return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


def _compile_concatenated_svg(tex_files: list[Path], preamble: str, output_svg: Path,
                               part_name: str, console=None) -> bool:
    """Compile all problems into a single concatenated SVG for standard tier."""
    bodies = []
    for tf in tex_files:
        content = tf.read_text()
        content_clean = "\n".join(
            l for l in content.split("\n")
            if not (l.strip().startswith("%") and re.match(r"%\s*\w+\s*:", l.strip()))
        )
        parts = _parse_tex(content_clean)
        if part_name in parts and parts[part_name].strip():
            bodies.append(parts[part_name].strip())

    if not bodies:
        return False

    combined = "\n\n".join(bodies)
    doc = preamble + "\n\\pagestyle{empty}\n\\begin{document}\n"
    if part_name in ("question", "combined"):
        doc += "\\begin{enumerate}[leftmargin=*]\n" + combined + "\n\\end{enumerate}\n"
    else:
        doc += combined + "\n"
    doc += "\\end{document}\n"

    return _compile_to_svg(doc, output_svg, console)




# ===================================================================
# Zip subcommand (for zipping existing archive folders)
# ===================================================================

@click.command("zip", context_settings=CONTEXT_SETTINGS)
@click.argument("archive_dir", type=click.Path(exists=True), default="archive")
@click.option("--output", "-o", help="Output zip filename (default: <archive_dir>.zip)")
def zip_archive(archive_dir, output):
    """Create a ZIP file from an existing archive directory.

    \b
    Examples:
        vbagent archive zip                    # zips ./archive to archive.zip
        vbagent archive zip my-archive         # zips ./my-archive to my-archive.zip
        vbagent archive zip archive -o pyq.zip # zips ./archive to pyq.zip
    """
    console = _get_console()
    archive_path = Path(archive_dir)
    
    if not archive_path.is_dir():
        console.print(f"[red]Error: {archive_dir} is not a directory[/red]")
        return
    
    # Determine output zip name
    if output:
        zip_name = output if output.endswith('.zip') else f"{output}.zip"
        zip_path = archive_path.parent / zip_name
    else:
        zip_path = archive_path.parent / f"{archive_path.name}.zip"
    
    # Remove existing zip if present
    if zip_path.exists():
        console.print(f"[yellow]Removing existing {zip_path.name}[/yellow]")
        zip_path.unlink()
    
    console.print(f"[cyan]Creating {zip_path.name}...[/cyan]")
    shutil.make_archive(
        str(zip_path.with_suffix('')),  # without .zip extension
        "zip",
        str(archive_path.parent),
        archive_path.name
    )
    
    console.print(f"[green]✓[/green] {zip_path} ({_human_size(zip_path)})")


# ===================================================================
# Product subcommand
# ===================================================================

@click.command("product", context_settings=CONTEXT_SETTINGS)
@click.argument("scans_dir", type=click.Path(exists=True), default="agentic/scans")
@click.option("--output", "-o", default="product-archive", help="Output directory")
@click.option("--title", "-t", required=True, help="Product title")
@click.option("--subject", "-s", type=click.Choice(["physics", "chemistry", "mathematics"]))
@click.option("--exam", "-e", default="jee", type=click.Choice(["jee", "neet", "jee_advanced"]))
@click.option("--chapter", "-c", multiple=True, help="Chapter(s) — can repeat")
@click.option("--price-standard", type=int, required=True, help="Standard price in ₹")
@click.option("--price-premium", type=int, required=True, help="Premium price in ₹")
@click.option("--description-file", type=click.Path(exists=True), help="Custom description.md")
@click.option("--thumbnail", type=click.Path(exists=True), help="Custom thumbnail.png")
@click.option("--zip/--no-zip", "make_zip", default=True)
@click.option("--from", "from_num", type=int, default=None)
@click.option("--to", "to_num", type=int, default=None)
def product(scans_dir, output, title, subject, exam, chapter, price_standard, price_premium,
            description_file, thumbnail, make_zip, from_num, to_num):
    """Export scans as product upload ZIP.

    \b
    Output: standard/ (concatenated SVGs) + premium/problems/ (per-problem SVGs)
    
    \b
    Examples:
        vbagent archive product --title "Kinematics — 50" --price-standard 299 --price-premium 499
        vbagent archive product -t "EMI Problems" -c "electromagnetic induction" -c "ac circuits" \\
            --price-standard 199 --price-premium 399
    """
    console = _get_console()
    scans_path = Path(scans_dir)
    output_path = Path(output)
    tex_files = _discover_tex_files(scans_path, from_num, to_num)
    if not tex_files:
        console.print(f"[red]No .tex files in {scans_dir}[/red]")
        return

    if not subject:
        from vbagent.config import get_config
        subject = get_config().subject

    preamble = _get_preamble(subject)
    chapters = list(chapter) if chapter else []
    console.print(f"[cyan]Building product archive: {title} ({len(tex_files)} problems)[/cyan]")

    # --- Aggregate metadata from all classifications ---
    all_topics: list[str] = []
    all_difficulties: list[int] = []
    type_counts: Counter = Counter()

    for tf in tex_files:
        cls = _load_classification(scans_path, tf.stem)
        topics = _extract_topics(cls, tf.read_text(), scans_path, tf.stem)
        all_topics.extend(topics)
        d = cls.get("difficulty_score")
        if d:
            try:
                all_difficulties.append(int(d))
            except (ValueError, TypeError):
                pass
        type_counts[cls.get("question_type", "mcq_sc")] += 1
        if not chapters and cls.get("chapter"):
            chapters.append(cls["chapter"])

    unique_topics = list(dict.fromkeys(t.lower() for t in all_topics if t))
    chapters = list(dict.fromkeys(c.lower() for c in chapters if c))
    diff_range = [min(all_difficulties, default=4), max(all_difficulties, default=8)]
    content_type = "chapter" if len(chapters) <= 1 else "module"

    metadata = {
        "title": title,
        "description": title,
        "subject": subject,
        "exam": exam,
        "content_type": content_type,
        "chapters": chapters,
        "topics": unique_topics[:20],
        "difficulty_range": diff_range,
        "price_standard": price_standard,
        "price_premium": price_premium,
        "problem_count": len(tex_files),
    }

    # --- Standard tier: concatenated SVGs ---
    std_dir = output_path / "standard"
    std_dir.mkdir(parents=True, exist_ok=True)
    console.print("[dim]Compiling standard tier...[/dim]")
    for part in ["problem", "solution", "combined"]:
        # Map part names: "problem" → "question" in _parse_tex
        parse_key = "question" if part == "problem" else part
        ok = _compile_concatenated_svg(tex_files, preamble, std_dir / f"{part}.svg", parse_key, console)
        if ok:
            console.print(f"  [green]✓[/green] standard/{part}.svg")
        else:
            console.print(f"  [yellow]⚠[/yellow] standard/{part}.svg failed")

    # --- Premium tier: per-problem SVGs ---
    prem_dir = output_path / "premium" / "problems"
    console.print("[dim]Compiling premium tier...[/dim]")
    ok_count, fail_count = 0, 0
    for idx, tf in enumerate(tex_files, 1):
        prob_dir = prem_dir / str(idx)
        prob_dir.mkdir(parents=True, exist_ok=True)
        results = _render_parts(tf, preamble, prob_dir, console)
        if any(not v for v in results.values()):
            fail_count += 1
        else:
            ok_count += 1
    console.print(f"  [green]✓[/green] {ok_count} problems compiled, {fail_count} with errors")

    # --- Description ---
    if description_file:
        shutil.copy2(description_file, output_path / "description.md")
        console.print("[green]✓[/green] description.md (provided)")
    else:
        console.print("[dim]Generating description...[/dim]")
        desc = _generate_description_md(metadata)
        (output_path / "description.md").write_text(desc)
        console.print("[green]✓[/green] description.md (generated)")

    # --- Thumbnail ---
    if thumbnail:
        shutil.copy2(thumbnail, output_path / "thumbnail.png")
        console.print("[green]✓[/green] thumbnail.png (provided)")
    else:
        tikz_dir = scans_path.parent / "tikz"
        if _generate_thumbnail(tikz_dir, output_path / "thumbnail.png", preamble, console):
            console.print("[green]✓[/green] thumbnail.png (generated from TikZ)")
        else:
            console.print("[dim]⚠ No thumbnail generated (no TikZ diagrams found)[/dim]")

    # --- Metadata ---
    (output_path / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    console.print("[green]✓[/green] metadata.json")

    # --- ZIP ---
    if make_zip:
        zip_path = output_path.parent / f"{output_path.name}.zip"
        shutil.make_archive(str(output_path), "zip", str(output_path.parent), output_path.name)
        console.print(f"\n[green]✓[/green] {zip_path} ({_human_size(zip_path)})")

    console.print(f"\n[cyan]Done:[/cyan] {title} — {len(tex_files)} problems")


# ===================================================================
# Main archive group
# ===================================================================

@click.group(context_settings=CONTEXT_SETTINGS)
def archive():
    """Export scans as structured ZIP for platform upload.

    \b
    Subcommands:
        pyq      — PYQ bulk upload (per-problem folders + metadata)
        product  — Product upload (standard + premium tiers)
        zip      — Create ZIP from existing archive directory

    \b
    Examples:
        vbagent archive pyq --exam neet --year 2024 --chapter "atoms and nuclei"
        vbagent archive product --title "Kinematics" --price-standard 299 --price-premium 499
        vbagent archive zip                    # zip the archive folder
    """
    pass


archive.add_command(pyq)
archive.add_command(zip_archive)
archive.add_command(product)
