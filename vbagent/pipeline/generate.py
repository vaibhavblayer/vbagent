"""Generation pipeline — create problems from ideas, sketches, or topics.

Orchestrates: SketchReader → IdeaGenerator → TikZ → Solution → Save.
Every LLM call is saved to disk under ``Gen_N/llm_calls/`` for full
traceability.  Results are cached by idea hash so re-runs skip the LLM.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from vbagent.cli.common import _get_console, format_latex
from vbagent.config import get_config


# ---------------------------------------------------------------------------
# LLM call saving
# ---------------------------------------------------------------------------

def _save_llm_call(
    calls_dir: Path,
    stage: str,
    agent_name: str,
    input_data: Any,
    output_data: Any,
    duration: float = 0.0,
    extra: dict | None = None,
) -> Path:
    """Save a single LLM call's input/output to disk.

    Creates ``calls_dir/<NN>_<stage>.json`` with the full
    request context and response for debugging and auditing.

    Args:
        calls_dir: Directory to save into (e.g. mode_dir/llm_calls/problem_1/).
        stage: Short label like ``sketch_analysis``, ``idea_generation``, ``tikz``.
        agent_name: Name of the agent that ran.
        input_data: The input sent to the agent (str, list, or dict).
        output_data: The agent's output (Pydantic model, str, or dict).
        duration: Wall-clock seconds the call took.
        extra: Any additional metadata to include.

    Returns:
        Path to the saved JSON file.
    """
    calls_dir.mkdir(parents=True, exist_ok=True)

    # Auto-number: count existing files to get next index
    existing = sorted(calls_dir.glob("*.json"))
    idx = len(existing) + 1

    # Serialize output
    if hasattr(output_data, "model_dump"):
        out_serialized = output_data.model_dump()
    elif isinstance(output_data, str):
        out_serialized = output_data
    elif isinstance(output_data, dict):
        out_serialized = output_data
    else:
        out_serialized = str(output_data)

    # Serialize input — strip base64 images for readability
    if isinstance(input_data, str):
        in_serialized = input_data
    elif isinstance(input_data, list):
        in_serialized = _sanitize_input_for_save(input_data)
    elif isinstance(input_data, dict):
        in_serialized = input_data
    else:
        in_serialized = str(input_data)

    payload = {
        "stage": stage,
        "agent": agent_name,
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": round(duration, 2),
        "input": in_serialized,
        "output": out_serialized,
    }
    if extra:
        payload["extra"] = extra

    filename = f"{idx:02d}_{stage}.json"
    path = calls_dir / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return path


def _sanitize_input_for_save(input_data: list) -> list:
    """Strip base64 image data from message lists before saving to disk."""
    import re
    sanitized = []
    for item in input_data:
        if not isinstance(item, dict):
            sanitized.append(item)
            continue
        item_copy = dict(item)
        content = item_copy.get("content")
        if isinstance(content, list):
            new_content = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "input_image":
                    url = part.get("image_url", "")
                    # Replace base64 data with a placeholder
                    if "base64," in url:
                        media = url.split(";base64,")[0] if ";base64," in url else "image"
                        new_content.append({
                            "type": "input_image",
                            "image_url": f"{media};base64,[{len(url)}chars]",
                            "detail": part.get("detail", "auto"),
                        })
                    else:
                        new_content.append(part)
                else:
                    new_content.append(part)
            item_copy["content"] = new_content
        sanitized.append(item_copy)
    return sanitized


# ---------------------------------------------------------------------------
# Generation cache — hash-based dedup so re-runs skip the LLM
# ---------------------------------------------------------------------------
def _idea_hash(ideas: list[str], concepts: list[str], topic: str,
               difficulty: str, question_type: str, subject: str) -> str:
    """Deterministic hash of the generation inputs (for metadata only)."""
    blob = json.dumps({
        "ideas": sorted(ideas),
        "concepts": sorted(concepts),
        "topic": topic,
        "difficulty": difficulty,
        "question_type": question_type,
        "subject": subject,
    }, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Diagram-type inference from description keywords
# ---------------------------------------------------------------------------

def _infer_diagram_type(description: str, subject: str) -> str | None:
    """Infer a diagram_type string from a free-text diagram description.

    This gives the TikZ router a concrete type to match against instead
    of falling back to the generic agent.
    """
    desc = description.lower()
    subject_lower = subject.lower()

    if subject_lower == "physics":
        if any(kw in desc for kw in [
            "circuit", "resistor", "capacitor", "inductor", "battery",
            "emf", "rail", "solenoid", "coil", "wheatstone", "potentiometer",
            "galvanometer", "ammeter", "voltmeter", "transformer", "diode",
        ]):
            return "circuit"
        if any(kw in desc for kw in [
            "free body", "fbd", "force diagram", "block", "pulley",
            "incline", "wedge", "spring", "tension", "friction",
        ]):
            return "fbd"
        if any(kw in desc for kw in [
            "ray", "lens", "mirror", "prism", "optic", "refraction",
            "reflection", "focal",
        ]):
            return "optics"
        if any(kw in desc for kw in [
            "graph", "plot", "v-t", "x-t", "a-t", "curve", "axes",
        ]):
            return "graph"

    elif subject_lower == "chemistry":
        if any(kw in desc for kw in [
            "organic", "structure", "molecule", "benzene", "chemfig",
            "alkane", "alkene", "alkyne", "functional group",
        ]):
            return "organic_structure"
        if any(kw in desc for kw in [
            "mechanism", "arrow pushing", "nucleophil", "electrophil",
            "substitution", "elimination",
        ]):
            return "reaction_mechanism"
        if any(kw in desc for kw in ["orbital", "electron config", "mo diagram"]):
            return "orbital"
        if any(kw in desc for kw in [
            "energy diagram", "enthalpy", "born haber", "activation energy",
            "reaction coordinate",
        ]):
            return "energy_diagram"
        if any(kw in desc for kw in ["equation", "reaction scheme"]):
            return "chemical_equation"

    elif subject_lower == "mathematics":
        if any(kw in desc for kw in ["number line", "inequality", "interval"]):
            return "number_line"
        if any(kw in desc for kw in ["venn", "set"]):
            return "venn_diagram"
        if any(kw in desc for kw in [
            "function", "calculus", "derivative", "integral", "tangent",
        ]):
            return "function_graph"
        if any(kw in desc for kw in [
            "coordinate", "conic", "parabola", "ellipse", "hyperbola",
            "circle", "line",
        ]):
            return "coordinate_geometry"
        if any(kw in desc for kw in [
            "triangle", "polygon", "angle", "quadrilateral", "geometric",
        ]):
            return "geometric_figure"

    return None


class GenerationResult:
    """Result from a single problem generation."""

    def __init__(
        self,
        base_name: str,
        output_dir: Path,
        problem_tex: str = "",
        solution_tex: str = "",
        tikz_code: str | None = None,
        idea_latex: str = "",
        sketch_analysis: dict | None = None,
        generation_meta: dict | None = None,
        source: str = "topic",
        elapsed: float = 0.0,
    ):
        self.base_name = base_name
        self.output_dir = output_dir
        self.problem_tex = problem_tex
        self.solution_tex = solution_tex
        self.tikz_code = tikz_code
        self.idea_latex = idea_latex
        self.sketch_analysis = sketch_analysis
        self.generation_meta = generation_meta or {}
        self.source = source
        self.elapsed = elapsed


def _numeric_sort_key(path: Path) -> tuple:
    """Sort key that orders files numerically: problem_2 before problem_10."""
    import re
    m = re.search(r'(\d+)', path.stem)
    return (int(m.group(1)),) if m else (float('inf'), path.stem)


def _extract_file_number(filename: str) -> int | None:
    """Extract the trailing number from a filename like problem_10.tex → 10."""
    import re
    m = re.search(r'(\d+)', Path(filename).stem)
    return int(m.group(1)) if m else None


def _load_ideas_from_dir(ideas_dir: Path) -> list[dict]:
    """Load IdeaResult JSON files from a directory (numerically sorted)."""
    results = []
    if not ideas_dir.exists():
        return results
    for f in sorted(ideas_dir.glob("*.json"), key=_numeric_sort_key):
        try:
            data = json.loads(f.read_text())
            data["_source_file"] = f.name
            results.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return results


def _extract_ideas_from_scans(scans_dir: Path) -> list[dict]:
    """Extract \\begin{idea}...\\end{idea} blocks from scan .tex files.

    Also tries to extract a topic hint from the idea content (first
    \\textbf{Concept:} line or \\intertext{\\textbf{...}} pattern).
    """
    import re

    results = []
    if not scans_dir.exists():
        return results
    for f in sorted(scans_dir.glob("*.tex"), key=_numeric_sort_key):
        content = f.read_text()
        matches = re.findall(
            r"\\begin\{idea\}(.*?)\\end\{idea\}", content, re.DOTALL
        )
        for idea_text in matches:
            idea_text = idea_text.strip()
            # Try to extract a topic from the idea content
            topic = ""
            # Pattern: \textbf{Concept:} ... or \intertext{\textbf{Concept:} ...}
            concept_match = re.search(
                r"\\textbf\{Concept:\}\s*(.+?)(?:\\\\|$|\})", idea_text
            )
            if concept_match:
                topic = concept_match.group(1).strip().rstrip("}")
            if not topic:
                # Fallback: \intertext{...} first line
                intertext_match = re.search(
                    r"\\intertext\{(.+?)\}", idea_text
                )
                if intertext_match:
                    topic = intertext_match.group(1).strip()
                    # Remove \textbf{} wrapper if present
                    topic = re.sub(r"\\textbf\{(.*?)\}", r"\1", topic)

            results.append({
                "_source_file": f.name,
                "idea_latex": idea_text,
                "topic": topic,
                "concepts": [],
                "formulas": [],
                "techniques": [],
            })
    return results



def _save_generation(result: GenerationResult) -> dict[str, str]:
    """Save all generation artifacts to the output directory.

    Structure mirrors the ``run`` command output:
        agentic/generated/<source_mode>/
        ├── problems/{base_name}.tex     # Combined problem + solution + idea (TikZ injected)
        ├── tikz/{base_name}.tex         # TikZ diagram (if any)
        ├── llm_calls/{base_name}/       # Every LLM call for this problem
        │   ├── 01_sketch_analysis.json
        │   ├── 02_idea_generation.json
        │   └── 03_tikz.json
        ├── sketch_analysis/{base_name}.json  # SketchReader output (if from image)
        └── generation/{base_name}.json       # Metadata
    """
    out = result.output_dir
    out.mkdir(parents=True, exist_ok=True)
    name = result.base_name
    saved = {}

    # Combined .tex: problem → diagram → solution → idea
    combined = result.problem_tex

    if result.tikz_code and combined:
        from vbagent.pipeline.io import insert_tikz_into_latex
        injected = insert_tikz_into_latex(combined, result.tikz_code)
        if injected != combined:
            # Placeholder was found and replaced — good
            combined = injected
        else:
            # No placeholder — append diagram after the problem text
            if "\\begin{center}" not in result.tikz_code:
                tikz_block = f"\\begin{{center}}\n{result.tikz_code}\n\\end{{center}}"
            else:
                tikz_block = result.tikz_code
            combined = combined + "\n\n" + tikz_block

    if result.solution_tex:
        combined += "\n\n" + result.solution_tex
    if result.idea_latex:
        combined += "\n\n" + result.idea_latex

    problems_dir = out / "problems"
    problems_dir.mkdir(parents=True, exist_ok=True)
    tex_path = problems_dir / f"{name}.tex"
    tex_path.write_text(format_latex(combined))
    saved["problem"] = str(tex_path)

    # TikZ
    if result.tikz_code:
        tikz_dir = out / "tikz"
        tikz_dir.mkdir(parents=True, exist_ok=True)
        tikz_path = tikz_dir / f"{name}.tex"
        tikz_path.write_text(format_latex(result.tikz_code))
        saved["tikz"] = str(tikz_path)

    # Sketch analysis
    if result.sketch_analysis:
        sa_dir = out / "sketch_analysis"
        sa_dir.mkdir(parents=True, exist_ok=True)
        sa_path = sa_dir / f"{name}.json"
        sa_path.write_text(json.dumps(result.sketch_analysis, indent=2, ensure_ascii=False))
        saved["sketch_analysis"] = str(sa_path)

    # Generation metadata
    meta = {
        "base_name": name,
        "source": result.source,
        "elapsed_seconds": round(result.elapsed, 1),
        "subject": get_config().subject,
        **result.generation_meta,
    }
    gen_dir = out / "generation"
    gen_dir.mkdir(parents=True, exist_ok=True)
    meta_path = gen_dir / f"{name}.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    saved["generation"] = str(meta_path)

    return saved


def generate_from_sketch(
    image_path: str,
    question_type: str = "subjective",
    difficulty: str = "medium",
    topic_hint: str = "",
    with_solution: bool = True,
    with_diagram: bool = True,
    output_dir: Path | None = None,
    base_name: str = "sketch_1",
    console=None,
) -> tuple[str, str, str | None, dict]:
    """Generate a problem from a handwritten sketch image.

    Args:
        output_dir: If provided, saves every LLM call to output_dir/llm_calls/.

    Returns:
        (problem_tex, solution_tex, tikz_code, sketch_analysis_dict, idea_latex)
    """
    from vbagent.agents.content_generation.sketch_reader import analyze_sketch
    from vbagent.agents.classification.idea_generator import generate_from_idea

    console = console or _get_console()
    subject = get_config().subject

    # LLM calls dir: output_dir/llm_calls/{base_name}/
    llm_dir = (output_dir / "llm_calls" / base_name) if output_dir else None

    # Step 1: Analyze sketch
    console.print("[bold green]Analyzing sketch...[/bold green]")
    t1 = time.time()
    analysis = analyze_sketch(image_path, subject=subject)
    d1 = time.time() - t1
    console.print(f"  [cyan]Type:[/cyan] {analysis.sketch_type}")
    console.print(f"  [cyan]Topic:[/cyan] {analysis.topic_hint}")
    if analysis.equations:
        console.print(f"  [cyan]Equations:[/cyan] {', '.join(analysis.equations[:3])}")
    if analysis.diagram_description:
        console.print(f"  [cyan]Diagram:[/cyan] {analysis.diagram_description[:80]}...")

    # Save LLM call: sketch analysis
    if llm_dir:
        _save_llm_call(
            llm_dir, "sketch_analysis", f"SketchReader-{subject}",
            input_data=f"[image: {image_path}]",
            output_data=analysis, duration=d1,
            extra={"image_path": image_path},
        )

    # Use sketch analysis to build generation context
    effective_topic = topic_hint or analysis.topic_hint or subject
    effective_type = question_type or analysis.suggested_question_type
    effective_difficulty = difficulty or analysis.suggested_difficulty

    ideas = []
    if analysis.topic_hint:
        ideas.append(analysis.topic_hint)
    if analysis.what_to_find:
        ideas.append(f"Ask: {analysis.what_to_find}")
    if analysis.equations:
        ideas.append(f"Uses equations: {', '.join(analysis.equations)}")
    if analysis.diagram_description:
        ideas.append(f"Diagram: {analysis.diagram_description}")
    if analysis.values_given:
        vals = ", ".join(f"{k}={v}" for k, v in analysis.values_given.items())
        ideas.append(f"Given values: {vals}")
    if not ideas:
        ideas = [f"{subject} problem from sketch"]

    concepts = analysis.labels + list(analysis.values_given.keys())
    if not concepts:
        concepts = [effective_topic]

    # Step 2: Generate problem
    console.print("[bold green]Generating problem...[/bold green]")
    t2 = time.time()
    generated = generate_from_idea(
        ideas=ideas,
        concepts=concepts,
        topic=effective_topic,
        difficulty=effective_difficulty,
        question_type=effective_type,
        subject=subject,
    )
    d2 = time.time() - t2

    # Save LLM call: idea generation
    if llm_dir:
        _save_llm_call(
            llm_dir, "idea_generation", f"IdeaGenerator-{subject}",
            input_data={"ideas": ideas, "concepts": concepts,
                        "topic": effective_topic, "difficulty": effective_difficulty,
                        "question_type": effective_type},
            output_data=generated, duration=d2,
        )

    problem_tex = generated.problem_latex
    solution_tex = generated.solution_latex if with_solution else ""
    idea_tex = generated.idea_latex

    # Step 3: TikZ diagram
    tikz_code = None
    diagram_desc = generated.diagram_description or analysis.diagram_description
    if with_diagram and diagram_desc:
        # Infer diagram_type from description keywords for better routing
        inferred_type = _infer_diagram_type(diagram_desc, subject) or analysis.sketch_type
        t3 = time.time()
        tikz_code = _generate_tikz_for_problem(
            diagram_desc, subject, problem_tex, image_path,
            inferred_type, console,
        )
        d3 = time.time() - t3
        if llm_dir:
            _save_llm_call(
                llm_dir, "tikz", "TikZ-Router",
                input_data={"diagram_description": diagram_desc,
                            "sketch_type": analysis.sketch_type,
                            "inferred_type": inferred_type},
                output_data=tikz_code or "(failed)", duration=d3,
            )

    sketch_dict = analysis.model_dump()
    return problem_tex, solution_tex, tikz_code, sketch_dict, idea_tex


def generate_from_ideas_dir(
    ideas_dir: Path,
    scans_dir: Path | None = None,
    question_type: str = "subjective",
    difficulty: str = "medium",
    topic: str = "",
    with_solution: bool = True,
    with_diagram: bool = True,
    item_range: tuple[int, int] | None = None,
    output_base: Path | None = None,
    console=None,
) -> list[tuple[str, str, str | None, dict]]:
    """Generate problems from existing ideas JSON files or scan .tex files.

    Args:
        output_base: Source-mode directory (e.g. agentic/generated/scans/).
            LLM calls saved under output_base/llm_calls/{base_name}/.

    Returns list of (problem_tex, solution_tex, tikz_code, meta_dict, idea_latex).
    """
    from vbagent.agents.classification.idea_generator import generate_from_idea

    console = console or _get_console()
    subject = get_config().subject

    # Load ideas
    ideas_list = _load_ideas_from_dir(ideas_dir)
    if scans_dir:
        ideas_list.extend(_extract_ideas_from_scans(scans_dir))

    if not ideas_list:
        console.print("[red]No ideas found.[/red]")
        return []

    # Apply range filter — match by number in filename, not list index
    # e.g. --from 2 --to 5 means problem_2 through problem_5
    if item_range:
        start, end = item_range
        ideas_list = [
            idea for idea in ideas_list
            if (n := _extract_file_number(idea.get("_source_file", ""))) is not None
            and start <= n <= end
        ]

    console.print(f"[cyan]Found {len(ideas_list)} idea(s) to generate from[/cyan]")
    results = []

    for idx, idea_data in enumerate(ideas_list, 1):
        source_file = idea_data.get("_source_file", f"idea_{idx}")
        # Derive base_name from source file: problem_1.tex → problem_1
        base_name = Path(source_file).stem
        console.print(f"\n[bold]Generating {idx}/{len(ideas_list)} from {source_file}[/bold]")

        # LLM calls dir: output_base/llm_calls/{base_name}/
        llm_dir = (output_base / "llm_calls" / base_name) if output_base else None

        # Build ideas and concepts from the IdeaResult
        ideas = []
        if idea_data.get("topic"):
            ideas.append(idea_data["topic"])
        if idea_data.get("subtopic"):
            ideas.append(idea_data["subtopic"])
        for t in idea_data.get("techniques", []):
            ideas.append(t)
        if idea_data.get("idea_latex"):
            ideas.append(idea_data["idea_latex"][:200])
        if not ideas:
            ideas = [f"{subject} problem"]

        concepts = idea_data.get("concepts", []) + idea_data.get("formulas", [])
        if not concepts:
            concepts = [topic or subject]

        effective_topic = topic or idea_data.get("topic", "") or subject

        # Check cache — look for existing problems/{base_name}.tex
        cache_key = _idea_hash(ideas, concepts, effective_topic,
                               difficulty, question_type, subject)
        if output_base:
            problems_file = output_base / "problems" / f"{base_name}.tex"
            if problems_file.exists():
                console.print(f"  [cyan]↺ cached[/cyan] ({base_name})")
                cached_tex = problems_file.read_text()
                cached_tikz = None
                tikz_file = output_base / "tikz" / f"{base_name}.tex"
                if tikz_file.exists():
                    cached_tikz = tikz_file.read_text()
                meta = {"source_file": source_file, "base_name": base_name,
                        "cached": True, "cache_key": cache_key}
                results.append((cached_tex, "", cached_tikz, meta, ""))
                continue

        t1 = time.time()
        generated = generate_from_idea(
            ideas=ideas,
            concepts=concepts,
            topic=effective_topic,
            difficulty=difficulty,
            question_type=question_type,
            subject=subject,
        )
        d1 = time.time() - t1

        if llm_dir:
            _save_llm_call(
                llm_dir, "idea_generation", f"IdeaGenerator-{subject}",
                input_data={"ideas": ideas, "concepts": concepts,
                            "topic": effective_topic, "difficulty": difficulty,
                            "question_type": question_type,
                            "source_file": source_file},
                output_data=generated, duration=d1,
            )

        problem_tex = generated.problem_latex
        solution_tex = generated.solution_latex if with_solution else ""
        idea_latex = generated.idea_latex

        tikz_code = None
        diagram_desc = generated.diagram_description
        if with_diagram and diagram_desc:
            inferred_type = _infer_diagram_type(diagram_desc, subject)
            t2 = time.time()
            tikz_code = _generate_tikz_for_problem(
                diagram_desc, subject, problem_tex, None, inferred_type, console,
            )
            d2 = time.time() - t2
            if llm_dir:
                _save_llm_call(
                    llm_dir, "tikz", "TikZ-Router",
                    input_data={"diagram_description": diagram_desc,
                                "inferred_type": inferred_type},
                    output_data=tikz_code or "(failed)", duration=d2,
                )

        meta = {
            "source_file": source_file,
            "base_name": base_name,
            "source_ideas": ideas[:5],
            "source_concepts": concepts[:5],
            "cache_key": cache_key,
        }
        results.append((problem_tex, solution_tex, tikz_code, meta, idea_latex))

    return results


def generate_from_topic(
    topic: str,
    question_type: str = "subjective",
    difficulty: str = "medium",
    idea: str = "",
    with_solution: bool = True,
    with_diagram: bool = True,
    output_dir: Path | None = None,
    base_name: str = "topic_1",
    console=None,
) -> tuple[str, str, str | None, dict]:
    """Generate a problem from a topic string.

    Args:
        output_dir: If provided, saves LLM calls under output_dir/llm_calls/.

    Returns:
        (problem_tex, solution_tex, tikz_code, meta_dict, idea_latex)
    """
    from vbagent.agents.classification.idea_generator import generate_from_idea

    console = console or _get_console()
    subject = get_config().subject

    ideas = [idea] if idea else [f"{topic} problem"]
    concepts = [topic]

    # Check cache — look for existing problems/{base_name}.tex
    cache_key = _idea_hash(ideas, concepts, topic, difficulty, question_type, subject)
    if output_dir:
        problems_file = output_dir / "problems" / f"{base_name}.tex"
        if problems_file.exists():
            console.print(f"  [cyan]↺ cached[/cyan] ({base_name})")
            cached_tex = problems_file.read_text()
            cached_tikz = None
            tikz_file = output_dir / "tikz" / f"{base_name}.tex"
            if tikz_file.exists():
                cached_tikz = tikz_file.read_text()
            meta = {"topic": topic, "idea": idea, "base_name": base_name,
                    "cached": True, "cache_key": cache_key}
            return cached_tex, "", cached_tikz, meta, ""

    console.print(f"[bold green]Generating {topic} {question_type}...[/bold green]")

    # LLM calls dir
    llm_dir = (output_dir / "llm_calls" / base_name) if output_dir else None

    t1 = time.time()
    generated = generate_from_idea(
        ideas=ideas,
        concepts=concepts,
        topic=topic,
        difficulty=difficulty,
        question_type=question_type,
        subject=subject,
    )
    d1 = time.time() - t1

    if llm_dir:
        _save_llm_call(
            llm_dir, "idea_generation", f"IdeaGenerator-{subject}",
            input_data={"ideas": ideas, "concepts": concepts,
                        "topic": topic, "difficulty": difficulty,
                        "question_type": question_type},
            output_data=generated, duration=d1,
        )

    problem_tex = generated.problem_latex
    solution_tex = generated.solution_latex if with_solution else ""
    idea_latex = generated.idea_latex

    tikz_code = None
    diagram_desc = generated.diagram_description
    if with_diagram and diagram_desc:
        inferred_type = _infer_diagram_type(diagram_desc, subject)
        t2 = time.time()
        tikz_code = _generate_tikz_for_problem(
            diagram_desc, subject, problem_tex, None, inferred_type, console,
        )
        d2 = time.time() - t2
        if llm_dir:
            _save_llm_call(
                llm_dir, "tikz", "TikZ-Router",
                input_data={"diagram_description": diagram_desc,
                            "inferred_type": inferred_type},
                output_data=tikz_code or "(failed)", duration=d2,
            )

    meta = {
        "topic": topic,
        "idea": idea,
        "base_name": base_name,
        "diagram_description": diagram_desc or "",
        "cache_key": cache_key,
    }

    return problem_tex, solution_tex, tikz_code, meta, idea_latex


def _generate_tikz_for_problem(
    diagram_desc: str,
    subject: str,
    problem_tex: str,
    image_path: str | None,
    sketch_type: str | None,
    console,
) -> str | None:
    """Generate TikZ diagram for a generated problem."""
    from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
    from vbagent.models.classification import PrimaryClassification

    console.print("[bold green]Generating diagram...[/bold green]")
    try:
        # Build a minimal primary classification for routing
        primary = PrimaryClassification(
            subject=subject,
            question_type="subjective",
            has_diagram=True,
            confidence=1.0,
            classified_from="latex",
        )

        tikz_code, agent_used = generate_tikz_with_routing(
            image_path=image_path,
            description=diagram_desc,
            primary=primary,
            use_context=True,
            show_spinner=True,
            subject=subject,
            diagram_type=sketch_type,
            problem_text=problem_tex,
        )
        console.print(f"  [green]✓[/green] Diagram generated (agent: {agent_used})")
        return tikz_code
    except Exception as e:
        console.print(f"  [yellow]⚠[/yellow] Diagram failed: {e}")
        return None
