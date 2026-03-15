"""CLI command for full pipeline processing.

Orchestrates all agents for complete question processing across multiple subjects:
Classify → Scan → TikZ → Ideas → Variants.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import click

# Import common utilities
from vbagent.cli.common import (
    format_latex,
    extract_problem_solution,
    _get_console,
    _get_panel,
)
from vbagent.utils.tex_parser import parse_tex_file, extract_items

if TYPE_CHECKING:
    from vbagent.models.pipeline import PipelineResult
    from vbagent.models.classification import PrimaryClassification, DiagramAnalysis, DifficultyAssessment


# Module-level console for helper functions (lazy initialized)
_console = None


def _ensure_console():
    """Ensure console is initialized."""
    global _console
    if _console is None:
        _console = _get_console()
    return _console


def merge_metadata_into_latex(
    latex: str,
    primary: "PrimaryClassification",
    diagram: Optional["DiagramAnalysis"] = None,
    difficulty: Optional["DifficultyAssessment"] = None,
) -> str:
    """Prepend classification metadata as comments to LaTeX content."""
    comments = []
    
    # Basic metadata from Agent 1
    comments.append(f"% subject: {primary.subject}")
    comments.append(f"% type: {primary.question_type}")
    comments.append(f"% has_diagram: {primary.has_diagram}")
    
    # Use difficulty from Agent 3 if available
    if difficulty:
        comments.append(f"% difficulty: {difficulty.difficulty}")
    
    # Tags and concepts (from ClassificationResult, not PrimaryClassification)
    if hasattr(primary, 'key_concepts') and primary.key_concepts:
        comments.append(f"% key_concepts: {', '.join(primary.key_concepts)}")
    if difficulty and difficulty.tags_auto:
        comments.append(f"% tags: {', '.join(difficulty.tags_auto)}")
    
    # Diagram info
    if diagram:
        comments.append(f"% has_diagram: true")
        comments.append(f"% diagram_type: {diagram.diagram_type}")
        if diagram.diagram_elements:
            comments.append(f"% diagram_elements: {', '.join(diagram.diagram_elements)}")
    elif primary.has_diagram:
        comments.append(f"% has_diagram: true")
    
    # Difficulty details from Agent 3
    if difficulty:
        if difficulty.prerequisite_concepts:
            comments.append(f"% prerequisites: {', '.join(difficulty.prerequisite_concepts)}")
        if difficulty.cognitive_level:
            comments.append(f"% cognitive_level: {difficulty.cognitive_level}")
        comments.append(f"% estimated_time: {difficulty.expected_solve_time_minutes} min")
    
    # Join and prepend
    metadata_block = "\n".join(comments)
    return f"{metadata_block}\n\n{latex}"


def convert_primary_to_classification(primary: "PrimaryClassification") -> "ClassificationResult":
    """Convert PrimaryClassification to ClassificationResult for compatibility.
    
    Used when calling legacy functions that expect ClassificationResult.
    """
    from vbagent.models.classification import ClassificationResult
    return ClassificationResult(
        subject=primary.subject,
        question_type=primary.question_type,
        has_diagram=primary.has_diagram,
        confidence=primary.confidence,
        classified_from=primary.classified_from,
    )


def extract_items_from_tex(content: str) -> list[str]:
    """Extract individual items from a TeX file.
    
    Splits content by \\item markers to get individual problems.
    """
    return extract_items(content)


def filter_items_by_range(
    items: list[str],
    item_range: Optional[tuple[int, int]],
) -> list[str]:
    """Filter items by the specified range (1-based, inclusive)."""
    if not item_range:
        return items
    
    start, end = item_range
    start_idx = max(0, start - 1)
    end_idx = min(len(items), end)
    
    return items[start_idx:end_idx]


# extract_problem_solution and format_latex are imported from common module


def get_base_name(source_path: str) -> str:
    """Extract base name from source path (without extension)."""
    return Path(source_path).stem


def insert_tikz_into_latex(latex: str, tikz_code: str) -> str:
    """Replace diagram placeholders with actual TikZ code.
    
    Handles two types of placeholders:
    1. Main diagram: \\begin{center}\\input{diagram}\\end{center}
    2. Option diagrams: \\OptionA, \\OptionB, etc. with \\def definitions
    
    Args:
        latex: The LaTeX content with placeholder(s)
        tikz_code: The generated TikZ code (may include \\def\\OptionX{...})
        
    Returns:
        LaTeX with TikZ code inserted
    """
    result = latex
    
    # Check if tikz_code contains option definitions (\def\OptionA, etc.)
    has_option_defs = r'\def\Option' in tikz_code or r'\\def\\Option' in tikz_code
    
    if has_option_defs:
        # Insert option definitions before \begin{tasks}
        tasks_pattern = r'(% OPTIONS_DIAGRAMS:[^\n]*\n)?(\s*\\begin\{tasks\})'
        
        # Clean up the tikz_code - ensure proper escaping
        tikz_to_insert = tikz_code.strip()
        
        def replace_tasks(match):
            return f"{tikz_to_insert}\n{match.group(2)}"
        
        result = re.sub(tasks_pattern, replace_tasks, result)
        
        # Remove the OPTIONS_DIAGRAMS comment if present
        result = re.sub(r'% OPTIONS_DIAGRAMS:[^\n]*\n', '', result)
    else:
        # Handle main diagram placeholder
        # Pattern to match the placeholder (with flexible whitespace)
        placeholder_pattern = r'\\begin\{center\}\s*\\input\{diagram\}\s*\\end\{center\}'
        
        # Wrap TikZ code in center environment if not already wrapped
        if '\\begin{center}' not in tikz_code:
            tikz_wrapped = f"\\begin{{center}}\n{tikz_code}\n\\end{{center}}"
        else:
            tikz_wrapped = tikz_code
        
        # Replace placeholder with actual TikZ code
        # Use a function to avoid issues with backslash escaping
        def replace_diagram(match):
            return tikz_wrapped
        
        result = re.sub(placeholder_pattern, replace_diagram, result)
        
        # If no placeholder found, check for simpler pattern
        if result == latex:
            simple_pattern = r'\\input\{diagram\}'
            if re.search(simple_pattern, latex):
                result = re.sub(simple_pattern, lambda m: tikz_code, result)
    
    return result


def _generate_context_file(output_path: Path, problem_count: int) -> None:
    """Generate CONTEXT.md file for external AI agents.
    
    Creates a documentation file in the output directory that helps
    external AI tools (Codex, Claude Code, Cursor, etc.) understand
    the directory structure and work with physics problems.
    
    Args:
        output_path: Output directory path
        problem_count: Number of problems processed
    """
    from vbagent.templates.agentic_context import generate_context_file
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    content = generate_context_file(
        directory_name=output_path.name,
        problem_count=problem_count,
    )
    
    context_file = output_path / "CONTEXT.md"
    context_file.write_text(content)


def generate_image_paths_from_range(
    image_path: str,
    item_range: tuple[int, int],
) -> list[str]:
    """Generate image paths from a template and range.
    
    Given an image path like 'images/Problem_3.png' and range (1, 5),
    generates paths: Problem_1.png, Problem_2.png, ..., Problem_5.png
    
    Supports patterns:
    - Problem_3.png -> Problem_1.png, Problem_2.png, ...
    - question3.png -> question1.png, question2.png, ...
    - img_03.png -> img_01.png, img_02.png, ...
    """
    path = Path(image_path)
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    
    # Find the number pattern in the filename
    # Match trailing number with optional underscore/hyphen prefix
    match = re.search(r'([_\-]?)(\d+)$', stem)
    
    if not match:
        # No number found, can't generate range
        return [image_path]
    
    prefix = stem[:match.start()]
    separator = match.group(1)  # underscore, hyphen, or empty
    num_str = match.group(2)
    num_width = len(num_str)  # preserve zero-padding width
    
    start, end = item_range
    paths = []
    
    for i in range(start, end + 1):
        # Format number with same width (zero-padded if original was)
        new_num = str(i).zfill(num_width)
        new_stem = f"{prefix}{separator}{new_num}"
        new_path = parent / f"{new_stem}{suffix}"
        
        if new_path.exists():
            paths.append(str(new_path))
        else:
            _get_console().print(f"[yellow]Warning:[/yellow] Image not found: {new_path}")
    
    return paths


def save_pipeline_result_organized(
    result: PipelineResult,
    base_dir: Path,
    base_name: str,
) -> dict[str, str]:
    """Save pipeline result to organized directory structure.
    
    Structure:
        agentic/
        ├── scans/{base_name}.tex
        ├── classifications/{base_name}.json
        ├── alternates/{base_name}.tex
        ├── variants/
        │   ├── numerical/{base_name}.tex
        │   ├── context/{base_name}.tex
        │   └── ...
        ├── ideas/{base_name}.json
        └── tikz/{base_name}.tex
    
    Returns dict mapping output type to file path.
    """
    saved_files = {}
    
    # Save scanned LaTeX (with formatting)
    scans_dir = base_dir / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)
    latex_path = scans_dir / f"{base_name}.tex"
    latex_path.write_text(format_latex(result.latex))
    saved_files["scan"] = str(latex_path)
    
    # Save classification
    class_dir = base_dir / "classifications"
    class_dir.mkdir(parents=True, exist_ok=True)
    class_path = class_dir / f"{base_name}.json"
    class_path.write_text(result.classification.model_dump_json(indent=2))
    saved_files["classification"] = str(class_path)
    
    # Save TikZ if present (with formatting)
    if result.tikz_code:
        tikz_dir = base_dir / "tikz"
        tikz_dir.mkdir(parents=True, exist_ok=True)
        tikz_path = tikz_dir / f"{base_name}.tex"
        tikz_path.write_text(format_latex(result.tikz_code))
        saved_files["tikz"] = str(tikz_path)
    
    # Save ideas if present
    if result.ideas:
        ideas_dir = base_dir / "ideas"
        ideas_dir.mkdir(parents=True, exist_ok=True)
        ideas_path = ideas_dir / f"{base_name}.json"
        ideas_path.write_text(result.ideas.model_dump_json(indent=2))
        saved_files["ideas"] = str(ideas_path)
    
    # Save alternate solutions (with formatting)
    if result.alternate_solutions:
        alt_dir = base_dir / "alternates"
        alt_dir.mkdir(parents=True, exist_ok=True)
        alt_path = alt_dir / f"{base_name}.tex"
        formatted_alts = [format_latex(alt) for alt in result.alternate_solutions]
        combined = "\n\n% --- Alternate Solution ---\n\n".join(formatted_alts)
        alt_path.write_text(combined)
        saved_files["alternates"] = str(alt_path)
    
    # Save variants in subdirectories by type (with formatting)
    for variant_type, variant_latex in result.variants.items():
        variant_dir = base_dir / "variants" / variant_type
        variant_dir.mkdir(parents=True, exist_ok=True)
        variant_path = variant_dir / f"{base_name}.tex"
        variant_path.write_text(format_latex(variant_latex))
        saved_files[f"variant_{variant_type}"] = str(variant_path)
    
    return saved_files


def save_pipeline_result(result: PipelineResult, output_dir: Path) -> dict[str, str]:
    """Save pipeline result to output directory (legacy flat structure).
    
    Returns dict mapping output type to file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_files = {}
    
    # Save classification
    class_path = output_dir / "classification.json"
    class_path.write_text(result.classification.model_dump_json(indent=2))
    saved_files["classification"] = str(class_path)
    
    # Save LaTeX (with formatting)
    latex_path = output_dir / "scanned.tex"
    latex_path.write_text(format_latex(result.latex))
    saved_files["latex"] = str(latex_path)
    
    # Save TikZ if present (with formatting)
    if result.tikz_code:
        tikz_path = output_dir / "diagram.tex"
        tikz_path.write_text(format_latex(result.tikz_code))
        saved_files["tikz"] = str(tikz_path)
    
    # Save ideas if present
    if result.ideas:
        ideas_path = output_dir / "ideas.json"
        ideas_path.write_text(result.ideas.model_dump_json(indent=2))
        saved_files["ideas"] = str(ideas_path)
    
    # Save alternate solutions (with formatting)
    if result.alternate_solutions:
        alt_path = output_dir / "alternates.tex"
        formatted_alts = [format_latex(alt) for alt in result.alternate_solutions]
        combined = "\n\n% --- Alternate Solution ---\n\n".join(formatted_alts)
        alt_path.write_text(combined)
        saved_files["alternates"] = str(alt_path)
    
    # Save variants (with formatting)
    for variant_type, variant_latex in result.variants.items():
        variant_path = output_dir / f"variant_{variant_type}.tex"
        variant_path.write_text(format_latex(variant_latex))
        saved_files[f"variant_{variant_type}"] = str(variant_path)
    
    # Save full result as JSON
    result_path = output_dir / "pipeline_result.json"
    result_path.write_text(result.model_dump_json(indent=2))
    saved_files["full_result"] = str(result_path)
    
    return saved_files


def _process_images_parallel(
    image_paths: list[str],
    variant_types: list[str],
    generate_alternate: bool,
    generate_ideas: bool,
    use_context: bool,
    output_dir: str,
    num_workers: int,
    console,
    assess_difficulty: bool,
    analyze_diagram: bool,
    merge_metadata: bool,
    use_orchestrator: bool,
    use_cache: bool,
    generate_solution: bool,
) -> tuple[list, int]:
    """Process multiple images in parallel using ThreadPoolExecutor.
    
    Args:
        image_paths: List of image paths to process
        variant_types: Variant types to generate
        generate_alternate: Whether to generate alternate solutions
        generate_ideas: Whether to extract ideas
        use_context: Whether to use reference context
        output_dir: Output directory for results
        num_workers: Number of parallel workers
        console: Rich console for output
        assess_difficulty: Whether to assess difficulty
        analyze_diagram: Whether to analyze diagram
        merge_metadata: Whether to merge metadata
        use_orchestrator: Whether to use orchestrator
        use_cache: Whether to use cache
        generate_solution: Whether to use new solution generation pipeline
        
    Returns:
        Tuple of (results list, failed count)
    """
    import concurrent.futures
    import threading
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    
    results = []
    failed_count = 0
    output_path = Path(output_dir)
    
    # Thread-safe counters
    lock = threading.Lock()
    completed = {"success": 0, "failed": 0}
    
    def process_single_image(img_path: str) -> tuple[str, Optional["PipelineResult"], Optional[str]]:
        """Process a single image and return (path, result, error)."""
        try:
            result = process_image(
                image_path=img_path,
                variant_types=variant_types,
                generate_alternate=generate_alternate,
                generate_ideas=generate_ideas,
                use_context=use_context,
                assess_difficulty=assess_difficulty,
                analyze_diagram=analyze_diagram,
                merge_metadata=merge_metadata,
                use_orchestrator=use_orchestrator,
                use_cache=use_cache,
                generate_solution=generate_solution,
            )
            
            # Save immediately (thread-safe - each file is unique)
            base_name = get_base_name(result.source_path)
            save_pipeline_result_organized(result, output_path, base_name)
            
            return (img_path, result, None)
        except Exception as e:
            return (img_path, None, str(e))
    
    # Use progress bar for parallel processing
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"[cyan]Processing {len(image_paths)} images...",
            total=len(image_paths)
        )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(process_single_image, path): path
                for path in image_paths
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_path):
                img_path = future_to_path[future]
                img_name = Path(img_path).name
                
                try:
                    path, result, error = future.result()
                    
                    if error:
                        with lock:
                            completed["failed"] += 1
                        from .ui import print_status
                        print_status(console, f"{img_name}: {error}", "error")
                    else:
                        with lock:
                            completed["success"] += 1
                            results.append(result)
                        from .ui import print_status
                        print_status(console, img_name, "success")
                        
                except Exception as e:
                    with lock:
                        completed["failed"] += 1
                    from .ui import print_status
                    print_status(console, f"{img_name}: {e}", "error")
                
                progress.update(task, advance=1)
    
    return results, completed["failed"]


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-i", "--input", "--image", "--tex",
    "input_path",
    type=click.Path(exists=True),
    help="Input file path (image or tex file)"
)
@click.option(
    "--from", "from_index",
    type=int,
    default=None,
    help="Start index (1-based, inclusive)"
)
@click.option(
    "--to", "to_index",
    type=int,
    default=None,
    help="End index (1-based, inclusive)"
)
@click.option(
    "--item",
    type=int,
    default=None,
    help="Process single item (shorthand for --from N --to N)"
)
@click.option(
    "-r", "--range", "item_range",
    nargs=2,
    type=int,
    default=None,
    help="[DEPRECATED] Use --from and --to instead. Range to process (1-based inclusive)"
)
@click.option(
    "--variants", "variant_types_str",
    type=str,
    default=None,
    help="Variant types to generate (comma-separated: numerical,context,conceptual,calculus,cross_topic). Disabled by default."
)
@click.option(
    "--alternate/--no-alternate",
    default=False,
    help="Generate alternate solutions (default: disabled)"
)
@click.option(
    "--ideas/--no-ideas",
    default=False,
    help="Extract key concepts and problem-solving ideas (default: disabled)"
)
@click.option(
    "--ref", "ref_dirs",
    multiple=True,
    type=click.Path(exists=True),
    help="Reference directories for TikZ generation"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    default="agentic",
    help="Output directory (default: agentic)"
)
@click.option(
    "--context/--no-context",
    default=True,
    help="Use reference context from ~/.config/vbagent (default: yes)"
)
@click.option(
    "-p", "--parallel",
    type=int,
    default=1,
    help="Number of images to process in parallel (default: 1, max: 5)"
)
@click.option(
    "-c", "--compile", "do_compile",
    is_flag=True,
    help="Compile generated LaTeX to validate"
)
@click.option(
    "--verbose-compile", "verbose_compile",
    is_flag=True,
    help="Show full LaTeX document before each compile"
)
@click.option(
    "--assess-difficulty/--no-assess-difficulty", "assess_difficulty",
    default=False,
    help="Assess difficulty after scanning [default: off]"
)
@click.option(
    "--analyze-diagram/--no-analyze-diagram", "analyze_diagram",
    default=True,
    help="Analyze diagram in detail [default: on]"
)
@click.option(
    "--validate-tikz", "validate_tikz",
    is_flag=True,
    help="Validate and fix TikZ code"
)
@click.option(
    "--orchestrate", "use_orchestrator",
    is_flag=True,
    help="Use solution orchestrator for complex solutions"
)
@click.option(
    "--merge-metadata/--no-merge-metadata", "merge_metadata",
    default=True,
    help="Merge classification metadata into scanned LaTeX [default: on]"
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable pipeline cache (force re-run all stages)"
)
@click.option(
    "--clear-cache",
    is_flag=True,
    help="Clear pipeline cache before processing"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output with additional details"
)
@click.option(
    "--generate-solution",
    is_flag=True,
    help="[EXPERIMENTAL] Use new solution generation pipeline with rich diagram context"
)
def process(
    input_path: Optional[str],
    from_index: Optional[int],
    to_index: Optional[int],
    item: Optional[int],
    item_range: Optional[tuple[int, int]],
    variant_types_str: Optional[str],
    alternate: bool,
    ideas: bool,
    ref_dirs: tuple[str, ...],
    output: str,
    context: bool,
    parallel: int,
    do_compile: bool,
    verbose_compile: bool,
    assess_difficulty: bool,
    analyze_diagram: bool,
    validate_tikz: bool,
    use_orchestrator: bool,
    merge_metadata: bool,
    no_cache: bool,
    clear_cache: bool,
    verbose: bool,
    generate_solution: bool,
):
    """Full pipeline: Classify → Scan → TikZ → Ideas → Variants.
    
    Orchestrates all agents for complete question processing across multiple subjects.
    Automatically detects subject (physics/chemistry/mathematics) and applies
    appropriate processing for each stage.
    
    By default, only classification, scanning, and TikZ generation run.
    Use --ideas, --alternate, and --variants to enable additional stages.
    
    \b
    Pipeline Stages:
        1. Classification - Detect subject and extract metadata
        2. Scanning - Extract LaTeX with subject-specific formatting
        3. TikZ - Generate diagram code (if has_diagram)
        4. Ideas - Extract key concepts (--ideas)
        5. Alternates - Generate alternate solutions (--alternate)
        6. Variants - Generate problem variants (--variants)
    
    \b
    Variant Types:
        numerical    - Change numerical values only
        context      - Change scenario/context only
        conceptual   - Change core concept
        calculus     - Add calculus-based modifications
        cross_topic  - Integrate a complementary topic (multi-stage)
    
    \b
    Output Structure:
        agentic/
        ├── scans/problem_1.tex
        ├── classifications/problem_1.json
        ├── alternates/problem_1.tex           (if --alternate)
        ├── variants/numerical/problem_1.tex   (if --variants)
        ├── variants/cross_topic/problem_1.tex (if --variants cross_topic)
        ├── ideas/problem_1.json               (if --ideas)
        └── tikz/problem_1.tex
    
    \b
    Examples:
        # Basic processing
        vbagent process -i images/Problem_1.png
        
        # With ideas and alternates
        vbagent process -i images/Problem_1.png --ideas --alternate
        
        # Generate variants
        vbagent process -i images/Problem_1.png --variants numerical,context
        
        # Chemistry question
        vbagent process -i chemistry/thermodynamics.png --ideas
        
        # Mathematics problem with variants
        vbagent process -i math/calculus.png --variants numerical,conceptual
        
        # Process range of images
        vbagent process -i images/Problem_1.png --from 1 --to 5
        
        # Parallel processing
        vbagent process -i images/Problem_1.png -r 1 10 --parallel 3
        
        # Process single item
        vbagent process -i images/Problem_1.png --item 3
        
        # Process TeX file
        vbagent process -i problems.tex --from 1 --to 5 --alternate --ideas
    
    \b
    Subject-Specific Processing:
        Physics: Vector notation, SI units, circuitikz, kinematikz
        Chemistry: \\ce{} notation, chemfig, mhchem, energy diagrams
        Mathematics: Proof structure, set notation, function graphs
    
    \b
    See Also:
        vbagent classify --help    # For classification options
        vbagent scan --help        # For scanning options
        vbagent batch --help       # For batch processing
    """
    # Lazy imports - only load heavy dependencies when command runs
    from vbagent.agents.classifier import classify as classify_image
    from vbagent.agents.content_generation.scanner import scan as scan_image
    from vbagent.agents.diagram.tikz import generate_tikz
    from vbagent.agents.content_generation.idea import extract_ideas
    from vbagent.agents.content_generation.alternate import generate_alternate as gen_alternate
    from vbagent.agents.variants.variant import generate_variant
    from vbagent.models.pipeline import PipelineResult
    from vbagent.references.store import ReferenceStore
    from vbagent.cache import PipelineCache
    
    console = _get_console()
    
    # Show deprecation warnings
    import sys
    if '--image' in sys.argv:
        console.print("[yellow]Note:[/yellow] --image is deprecated, use --input or -i", style="dim")
    if '--tex' in sys.argv:
        console.print("[yellow]Note:[/yellow] --tex is deprecated, use --input or -i", style="dim")
    if '--range' in sys.argv or '-r' in sys.argv:
        console.print("[yellow]Note:[/yellow] --range is deprecated, use --from and --to", style="dim")
    
    # Handle backward compatibility for range
    if item_range:
        from_index, to_index = item_range
    
    # Handle --item shorthand
    if item:
        from_index = to_index = item
    
    # Validate range
    if from_index and to_index and from_index > to_index:
        console.print("[red]Error:[/red] --from must be <= --to")
        raise SystemExit(1)
    
    # Convert to tuple for internal use (maintain compatibility with existing code)
    if from_index or to_index:
        item_range = (from_index or 1, to_index or 999999)  # Will be clamped later
    
    # Determine input type
    image = None
    tex = None
    if input_path:
        input_file = Path(input_path)
        if input_file.suffix.lower() in ['.tex', '.txt']:
            tex = input_path
        else:
            image = input_path
        
        if verbose:
            console.print(f"[dim]Input: {input_path}[/dim]")
            console.print(f"[dim]Type: {'TeX file' if tex else 'Image file'}[/dim]")
    
    # Handle cache flags
    use_cache = not no_cache
    if clear_cache:
        cache = PipelineCache()
        cache.clear()
        console.print("[yellow]✓[/yellow] Pipeline cache cleared")
        if not input_path:
            return  # Just clear cache and exit
    
    # Parse variant types from comma-separated string
    valid_variants = {"numerical", "context", "conceptual", "calculus", "cross_topic"}
    variant_types: list[str] = []
    if variant_types_str:
        for v in variant_types_str.replace(" ", "").split(","):
            if v and v in valid_variants:
                variant_types.append(v)
            elif v:
                console.print(f"[yellow]Warning:[/yellow] Unknown variant type '{v}', skipping")
    
    # Validate input
    if not input_path:
        console.print("[red]Error:[/red] --input is required")
        raise SystemExit(1)
    
    if verbose:
        console.print(f"[dim]Variants: {', '.join(variant_types) if variant_types else 'None'}[/dim]")
        console.print(f"[dim]Ideas: {'Yes' if ideas else 'No'}[/dim]")
        console.print(f"[dim]Alternates: {'Yes' if alternate else 'No'}[/dim]")
    
    try:
        # Initialize reference store if directories provided
        if ref_dirs:
            store = ReferenceStore.get_instance(directories=list(ref_dirs))
            with console.status("[bold blue]Indexing reference files..."):
                indexed_count = store.index_files()
            console.print(f"[dim]Indexed {indexed_count} reference files[/dim]")
        
        results: list[PipelineResult] = []
        
        if image:
            # Determine which images to process
            if item_range:
                # Generate image paths from range
                image_paths = generate_image_paths_from_range(image, item_range)
                if not image_paths:
                    console.print("[red]Error:[/red] No images found in specified range")
                    raise SystemExit(1)
                console.print(f"[cyan]Processing {len(image_paths)} image(s) in range {item_range[0]}-{item_range[1]}...[/cyan]")
            else:
                image_paths = [image]
            
            # Clamp parallel workers
            num_workers = min(max(1, parallel), len(image_paths), 10)
            
            if num_workers > 1 and len(image_paths) > 1:
                # Parallel processing with progress bar
                console.print(f"[cyan]Using {num_workers} parallel workers[/cyan]")
                results, failed_count = _process_images_parallel(
                    image_paths=image_paths,
                    variant_types=variant_types,
                    generate_alternate=alternate,
                    generate_ideas=ideas,
                    use_context=context,
                    output_dir=output,
                    num_workers=num_workers,
                    console=console,
                    assess_difficulty=assess_difficulty,
                    analyze_diagram=analyze_diagram,
                    merge_metadata=merge_metadata,
                    use_orchestrator=use_orchestrator,
                    use_cache=use_cache,
                    generate_solution=generate_solution,
                )
            else:
                # Sequential processing (single image or parallel=1)
                failed_count = 0
                for idx, img_path in enumerate(image_paths, 1):
                    if len(image_paths) > 1:
                        console.print(f"\n[bold]Image {idx}/{len(image_paths)}: {Path(img_path).name}[/bold]")
                    
                    try:
                        result = process_image(
                            image_path=img_path,
                            variant_types=variant_types,
                            generate_alternate=alternate,
                            generate_ideas=ideas,
                            use_context=context,
                            assess_difficulty=assess_difficulty,
                            analyze_diagram=analyze_diagram,
                            merge_metadata=merge_metadata,
                            use_orchestrator=use_orchestrator,
                            use_cache=use_cache,
                            generate_solution=generate_solution,
                        )
                        
                        # Compile validation if -c flag
                        if do_compile:
                            from vbagent.compile import compile_and_retry
                            from vbagent.agents.quality.latex_fixer import fix_latex
                            from vbagent.config import get_config as _get_cfg
                            _subj = _get_cfg().subject
                            
                            console.print("[dim]  → Compiling scanned LaTeX...[/dim]")
                            result.latex, _ = compile_and_retry(
                                result.latex, retry_fn=fix_latex,
                                subject=_subj, console=console,
                                verbose=verbose_compile,
                            )
                            if result.tikz_code:
                                console.print("[dim]  → Compiling TikZ...[/dim]")
                                result.tikz_code, _ = compile_and_retry(
                                    result.tikz_code, retry_fn=fix_latex,
                                    subject=_subj, console=console,
                                    verbose=verbose_compile,
                                )
                        
                        results.append(result)
                        
                        # Save immediately after each successful processing
                        output_path = Path(output)
                        base_name = get_base_name(result.source_path)
                        saved = save_pipeline_result_organized(result, output_path, base_name)
                        console.print(f"[green]✓ Saved {base_name}[/green]")
                        
                    except Exception as e:
                        console.print(f"[red]✗ Failed {Path(img_path).name}: {e}[/red]")
                        failed_count += 1
                        continue
        
        elif tex:
            # Process TeX file
            content = parse_tex_file(tex)
            items = extract_items_from_tex(content)
            
            if items:
                items = filter_items_by_range(items, item_range)
                console.print(f"[cyan]Processing {len(items)} item(s)...[/cyan]")
                
                for idx, item in enumerate(items, 1):
                    console.print(f"\n[bold]Item {idx}/{len(items)}[/bold]")
                    result = process_tex_item(
                        tex_content=item,
                        source_path=tex,
                        variant_types=variant_types,
                        generate_alternate=alternate,
                        generate_ideas=ideas,
                        use_context=context,
                    )
                    results.append(result)
            else:
                # Process entire content as single item
                result = process_tex_item(
                    tex_content=content,
                    source_path=tex,
                    variant_types=variant_types,
                    generate_alternate=alternate,
                    generate_ideas=ideas,
                    use_context=context,
                )
                results.append(result)
        
        # For TeX processing, save results (images are saved immediately above)
        output_path = Path(output)
        if tex and results:
            console.print(f"\n[cyan]Saving results to:[/cyan] {output_path}/")
            
            for result in results:
                base_name = get_base_name(result.source_path)
                saved = save_pipeline_result_organized(result, output_path, base_name)
                
                console.print(f"\n[green]Saved {base_name}:[/green]")
                for file_type, file_path in saved.items():
                    console.print(f"  • {file_type}: {file_path}")
        
        # Generate CONTEXT.md for external AI agents
        if results:
            _generate_context_file(output_path, len(results))
            console.print(f"\n[dim]Generated CONTEXT.md for external AI agents[/dim]")
        
        # Summary
        console.print(f"\n[bold green]Pipeline complete![/bold green]")
        if image:
            total = len(image_paths) if item_range else 1
            console.print(f"Processed {len(results)}/{total} image(s) successfully")
            if failed_count > 0:
                console.print(f"[yellow]Failed: {failed_count} image(s)[/yellow]")
        else:
            console.print(f"Processed {len(results)} item(s)")
        
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Pipeline failed:[/red] {e}")
        raise SystemExit(1)


def process_image(
    image_path: str,
    variant_types: list[str],
    generate_alternate: bool,
    generate_ideas: bool = False,
    use_context: bool = True,
    assess_difficulty: bool = True,
    analyze_diagram: bool = True,
    merge_metadata: bool = True,
    use_orchestrator: bool = False,
    use_cache: bool = True,
    problem_id: Optional[str] = None,
    generate_solution: bool = False,
) -> PipelineResult:
    """Process an image through the full pipeline.
    
    Pipeline stages:
    1. Classification (Agent 1 + optional Agent 2)
    2. Scanning (Agent 3 + optional difficulty assessment)
    3. TikZ (parallel with scanning if has_diagram)
    4. Ideas, Alternates, Variants (sequential, optional)
    
    Args:
        use_cache: If True, use cached results from previous runs
        problem_id: Problem identifier for caching (auto-generated if None)
    """
    import concurrent.futures
    import threading
    
    # Lazy imports
    from vbagent.agents.classification import classify_from_image, analyze_diagram as analyze_diagram_agent, assess_difficulty as assess_difficulty_agent
    from vbagent.cache import PipelineCache
    from vbagent.agents.content_generation.scanner import scan as scan_image
    from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
    from vbagent.agents.diagram.tikz import generate_tikz
    from vbagent.agents.content_generation.idea import extract_ideas
    from vbagent.agents.variants.variant import generate_variant
    from vbagent.models.pipeline import PipelineResult
    from vbagent.models.classification import ClassificationResult, PrimaryClassification, DiagramAnalysis
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    console = _get_console()
    
    # Initialize cache
    cache = PipelineCache() if use_cache else None
    if problem_id is None:
        problem_id = Path(image_path).stem
    
    # Show cached stages if any
    if cache:
        cached_stages = cache.get_cached_stages(problem_id)
        if cached_stages:
            console.print(f"[dim]Found cached: {', '.join(cached_stages)}[/dim]")
    
    # Stage 1: Classification with new multi-agent system
    primary = None
    if cache and cache.has(problem_id, "classification"):
        console.print("[dim]Loading cached classification...[/dim]")
        cached_data = cache.get(problem_id, "classification")
        primary = PrimaryClassification(**cached_data)
    else:
        with console.status("[bold green]Stage 1: Classifying image..."):
            primary = classify_from_image(image_path, show_spinner=False)
        if cache:
            cache.set(problem_id, "classification", primary.model_dump())
    
    console.print(f"[cyan]Type:[/cyan] {primary.question_type}")
    console.print(f"[cyan]Has Diagram:[/cyan] {'Yes' if primary.has_diagram else 'No'}")
    
    # Stage 1b: Diagram analysis (if enabled and has diagram)
    diagram_analysis = None
    if analyze_diagram and primary.has_diagram:
        if cache and cache.has(problem_id, "diagram"):
            console.print("[dim]Loading cached diagram analysis...[/dim]")
            cached_data = cache.get(problem_id, "diagram")
            diagram_analysis = DiagramAnalysis(**cached_data)
        else:
            with console.status("[bold green]Analyzing diagram..."):
                diagram_analysis = analyze_diagram_agent(image_path, primary, show_spinner=False)
            if cache:
                cache.set(problem_id, "diagram", diagram_analysis.model_dump())
        console.print(f"[cyan]Diagram Type:[/cyan] {diagram_analysis.diagram_type}")
    
    # Stage 2 & 3: Scanning + TikZ (PARALLEL if has_diagram) OR Orchestrator
    tikz_code = None
    latex = None
    difficulty_result = None
    
    # Use orchestrator if requested
    if use_orchestrator:
        console.print("[bold green]Stage 2: Solution Orchestrator...[/bold green]")
        from vbagent.agents.orchestration.solution_orchestrator import create_solution_orchestrator
        
        orchestrator = create_solution_orchestrator()
        
        problem_context = f"Question type: {primary.question_type}, Subject: {primary.subject}"
        
        orchestrator_result = orchestrator.generate_solution(
            image_path=image_path,
            problem_context=problem_context,
            question_type=primary.question_type,
            verbose=False,
        )
        
        latex = orchestrator_result.latex
        console.print(f"[green]✓ Solution generated using {len(orchestrator_result.agent_outputs)} specialist agents[/green]")
        
        # Extract TikZ if any agent generated it
        for output in orchestrator_result.agent_outputs:
            if output.agent in ["fbd", "circuit", "graph", "tikz", "ray_diagram", "optics"]:
                if tikz_code is None:
                    tikz_code = output.content
                else:
                    tikz_code += "\n\n" + output.content
    
    elif primary.has_diagram:
        # Check cache first
        latex_cached = cache and cache.has(problem_id, "scan")
        tikz_cached = cache and cache.has(problem_id, "tikz")
        
        if latex_cached and tikz_cached:
            console.print("[dim]Loading cached scan & TikZ...[/dim]")
            latex = cache.get(problem_id, "scan")
            tikz_code = cache.get(problem_id, "tikz")
            console.print("[green]✓[/green] Loaded from cache")
        else:
            # Run scanning and TikZ generation in parallel
            console.print("[bold green]Stage 2+3: Scanning & TikZ (parallel)...[/bold green]")
            
            # Prepare TikZ description based on classification
            tikz_description = f"Generate TikZ for {diagram_analysis.diagram_type if diagram_analysis else 'diagram'}"
            
            # Results holders
            scan_result_holder = {"result": None, "error": None}
            tikz_result_holder = {"result": None, "error": None, "agent": "generic"}
            
            def run_scan():
                if latex_cached:
                    scan_result_holder["result"] = type('obj', (object,), {'latex': cache.get(problem_id, "scan")})()
                    return
                try:
                    classification = convert_primary_to_classification(primary)
                    scan_result_holder["result"] = scan_image(
                        image_path, classification, use_context=use_context, subject=primary.subject, show_spinner=False
                    )
                except Exception as e:
                    scan_result_holder["error"] = e
            
            def run_tikz():
                if tikz_cached:
                    tikz_result_holder["result"] = cache.get(problem_id, "tikz")
                    return
                try:
                    if diagram_analysis:
                        # Use router with diagram analysis
                        tikz_code, agent_used = generate_tikz_with_routing(
                            image_path=image_path,
                            description=tikz_description,
                            diagram=diagram_analysis,
                            primary=primary,
                            use_context=use_context,
                            show_spinner=False
                        )
                        tikz_result_holder["result"] = tikz_code
                        tikz_result_holder["agent"] = agent_used
                    else:
                        # Fallback to generic TikZ (no diagram analysis available)
                        classification = convert_primary_to_classification(primary)
                        tikz_result_holder["result"] = generate_tikz(
                            description=tikz_description,
                            image_path=image_path,
                            use_context=use_context,
                            classification=classification,
                            show_spinner=False
                        )
                except Exception as e:
                    tikz_result_holder["error"] = e
            
            # Start both threads with combined spinner
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}[/bold cyan]"),
                console=console,
                transient=True
            )
            
            with progress:
                task = progress.add_task("Processing Scanner + TikZ...", total=None)
                
                scan_thread = threading.Thread(target=run_scan, daemon=True)
                tikz_thread = threading.Thread(target=run_tikz, daemon=True)
                
                scan_thread.start()
                tikz_thread.start()
                
                # Wait for both
                while scan_thread.is_alive() or tikz_thread.is_alive():
                    scan_thread.join(timeout=0.1)
                    tikz_thread.join(timeout=0.1)
            
            # Check for errors
            if scan_result_holder["error"]:
                raise scan_result_holder["error"]
            
            latex = scan_result_holder["result"].latex
            if cache and not latex_cached:
                cache.set(problem_id, "scan", latex)
            console.print("[green]✓[/green] Scanning complete")
            
            # TikZ errors are recoverable
            if tikz_result_holder["error"]:
                console.print(f"[yellow]![/yellow] TikZ generation failed: {tikz_result_holder['error']}")
                tikz_code = None
            else:
                tikz_code = tikz_result_holder["result"]
                if cache and not tikz_cached:
                    cache.set(problem_id, "tikz", tikz_code)
                agent_used = tikz_result_holder.get("agent", "generic")
                console.print(f"[green]✓[/green] TikZ complete (agent: {agent_used})")
            
            # Insert TikZ if needed
            if r'\input{diagram}' in latex:
                latex = insert_tikz_into_latex(latex, tikz_code)
        
        # Check if we need to handle option diagrams (detected after scanning)
        has_option_diagrams = r'\OptionA' in latex or r'\OptionB' in latex
        if has_option_diagrams:
            # Need to regenerate TikZ for option diagrams
            import re
            options_match = re.search(r'% OPTIONS_DIAGRAMS:\s*(.+?)(?:\n|$)', latex)
            if options_match:
                tikz_description = f"Generate option diagrams: {options_match.group(1)}"
            else:
                tikz_description = "Generate TikZ diagrams for MCQ options (\\OptionA, \\OptionB, \\OptionC, \\OptionD)"
            
            console.print("[dim]  → Generating option diagrams...[/dim]")
            # Use primary directly since classification may not be defined when cache is loaded
            classification_for_tikz = convert_primary_to_classification(primary)
            tikz_code = generate_tikz(
                description=tikz_description,
                image_path=image_path,
                use_context=use_context,
                classification=classification_for_tikz,
            )
            console.print("[green]  ✓ Option diagrams complete[/green]")
            console.print(_get_panel(tikz_code, title="Option Diagrams TikZ", border_style="cyan"))
        
        # Replace placeholders with actual TikZ code and show combined result
        if tikz_code and (r'\input{diagram}' in latex or has_option_diagrams):
            console.print("[dim]  → Combining LaTeX + TikZ...[/dim]")
            latex = insert_tikz_into_latex(latex, tikz_code)
            latex = format_latex(latex)
            console.print("[green]  ✓ Combined[/green]")
            console.print(_get_panel(latex, title="Final Combined LaTeX", border_style="green"))
        elif not tikz_code and r'\input{diagram}' in latex:
            # TikZ failed/timed out - keep placeholder for manual completion
            console.print("[yellow]  ⚠ Diagram placeholder kept - TikZ generation failed[/yellow]")
    else:
        # No diagram - just run scanning
        # NEW: Check if using solution generation pipeline
        if generate_solution:
            console.print("[bold green]Stage 2: NEW Solution Pipeline...[/bold green]")
            console.print("[dim]  → Scanning problem only[/dim]")
            from vbagent.agents.content_generation.scanner import scan_problem
            
            classification = convert_primary_to_classification(primary)
            problem_latex = scan_problem(
                image_path=image_path,
                question_type=classification.question_type,
                use_context=use_context,
                subject=primary.subject,
                show_spinner=True,
            )
            console.print("[green]  ✓ Problem scanned[/green]")
            
            console.print("[dim]  → Generating solution with rich context[/dim]")
            from vbagent.agents.content_generation.solution import generate_complete_solution
            
            solution_latex = generate_complete_solution(
                image_path=image_path,
                classification=classification,
                problem_text=problem_latex,
                subject=primary.subject,
                show_spinner=True,
            )
            console.print("[green]  ✓ Solution generated[/green]")
            
            # Combine
            latex = problem_latex + "\n\n" + solution_latex
            console.print("[green]✓[/green] Complete LaTeX generated using new solution pipeline")
        else:
            # Default: existing scanner
            console.print("[bold green]Stage 2: Scanning image...[/bold green]")
            classification = convert_primary_to_classification(primary)
            scan_result = scan_image(image_path, classification, use_context=use_context, subject=primary.subject)
            
            latex = scan_result.latex
            console.print("[green]✓[/green] Scanning complete")
        
        # Check for option diagrams even if has_diagram is False
        has_option_diagrams = r'\OptionA' in latex or r'\OptionB' in latex
        if has_option_diagrams:
            import re
            options_match = re.search(r'% OPTIONS_DIAGRAMS:\s*(.+?)(?:\n|$)', latex)
            if options_match:
                tikz_description = f"Generate option diagrams: {options_match.group(1)}"
            else:
                tikz_description = "Generate TikZ diagrams for MCQ options (\\OptionA, \\OptionB, \\OptionC, \\OptionD)"
            
            console.print("[bold green]Stage 3: Generating option diagrams...[/bold green]")
            console.print("[dim]  → Generating TikZ for options...[/dim]")
            tikz_code = generate_tikz(
                description=tikz_description,
                image_path=image_path,
                use_context=use_context,
                classification=classification,
            )
            console.print("[green]  ✓ Option diagrams complete[/green]")
            console.print(_get_panel(tikz_code, title="Option Diagrams TikZ", border_style="cyan"))
            
            console.print("[dim]  → Combining LaTeX + TikZ...[/dim]")
            latex = insert_tikz_into_latex(latex, tikz_code)
            latex = format_latex(latex)
            console.print("[green]  ✓ Combined[/green]")
            console.print(_get_panel(latex, title="Final Combined LaTeX", border_style="green"))
    
    # Stage 3b: Difficulty assessment (if enabled)
    if assess_difficulty:
        with console.status("[bold green]Assessing difficulty..."):
            difficulty_result = assess_difficulty_agent(latex, primary, diagram_analysis, show_spinner=False)
        console.print(f"[cyan]Difficulty:[/cyan] {difficulty_result.difficulty} ({difficulty_result.difficulty_score}/10)")
        console.print(f"[cyan]Cognitive Level:[/cyan] {difficulty_result.cognitive_level}")
        console.print(f"[cyan]Estimated Time:[/cyan] {difficulty_result.expected_solve_time_minutes} min")
    
    # Stage 3c: Merge metadata into LaTeX (if enabled)
    if merge_metadata:
        latex = merge_metadata_into_latex(latex, primary, diagram_analysis, difficulty_result)
        console.print("[green]✓[/green] Metadata merged into LaTeX")
    
    # Stage 4: Ideas (optional)
    problem, solution = extract_problem_solution(latex)
    ideas = None
    if generate_ideas and problem and solution:
        if cache and cache.has(problem_id, "ideas"):
            console.print("[dim]Loading cached ideas...[/dim]")
            from vbagent.models.content import IdeaResult
            ideas = IdeaResult(**cache.get(problem_id, "ideas"))
        else:
            with console.status("[bold green]Stage 4: Extracting ideas..."):
                ideas = extract_ideas(problem, solution)
            if cache:
                cache.set(problem_id, "ideas", ideas.model_dump())
        # Display ideas in a formatted panel
        ideas_text = f"[bold]Concepts:[/bold] {', '.join(ideas.concepts)}\n"
        ideas_text += f"[bold]Formulas:[/bold] {', '.join(ideas.formulas)}\n"
        ideas_text += f"[bold]Techniques:[/bold] {', '.join(ideas.techniques)}\n"
        ideas_text += f"[bold]Difficulty Factors:[/bold] {', '.join(ideas.difficulty_factors)}"
        console.print(_get_panel(ideas_text, title="Extracted Ideas", border_style="yellow"))
    
    # Stage 5: Alternates (optional)
    alternate_solutions = []
    if generate_alternate and problem and solution:
        if cache and cache.has(problem_id, "alternate"):
            console.print("[dim]Loading cached alternate...[/dim]")
            alt = cache.get(problem_id, "alternate")
            alternate_solutions.append(alt)
        else:
            with console.status("[bold green]Stage 5: Generating alternate solution..."):
                alt = generate_alternate_solution(problem, solution, ideas)
                alternate_solutions.append(alt)
            if cache:
                cache.set(problem_id, "alternate", alt)
        console.print(_get_panel(alt, title="Alternate Solution", border_style="magenta"))
    
    # Build classification result early so variants (especially cross_topic) can use it
    final_classification = ClassificationResult(
        subject=primary.subject,
        question_type=primary.question_type,
        has_diagram=primary.has_diagram,
        confidence=primary.confidence,
        classified_from=primary.classified_from,
    )
    
    # Stage 6: Variants (optional)
    variants = {}
    for vtype in variant_types:
        cache_key = f"variant_{vtype}"
        if cache and cache.has(problem_id, cache_key):
            console.print(f"[dim]Loading cached {vtype} variant...[/dim]")
            variant_latex = cache.get(problem_id, cache_key)
            variants[vtype] = variant_latex
        else:
            with console.status(f"[bold green]Stage 6: Generating {vtype} variant..."):
                variant_latex = generate_variant(
                    latex, vtype, ideas, use_context=use_context,
                    classification=final_classification,
                )
                variants[vtype] = variant_latex
            if cache:
                cache.set(problem_id, cache_key, variant_latex)
        console.print(_get_panel(variant_latex, title=f"{vtype.title()} Variant", border_style="green"))
    
    # Map v2 diagram_type to v1 enum
    v1_diagram_type = None
    if diagram_analysis:
        # Map detailed v2 types to v1 limited enum
        diagram_map = {
            "free_body": "free_body",
            "fbd": "free_body",
            "circuit": "circuit",
            "graph": "graph",
            "geometry": "geometry",
            "none": "none",
        }
        v1_diagram_type = diagram_map.get(diagram_analysis.diagram_type, "geometry")
    
    return PipelineResult(
        source_path=image_path,
        classification=final_classification,
        latex=latex,
        tikz_code=tikz_code,
        ideas=ideas,
        alternate_solutions=alternate_solutions,
        variants=variants,
    )


def process_tex_item(
    tex_content: str,
    source_path: str,
    variant_types: list[str],
    generate_alternate: bool,
    generate_ideas: bool = False,
    use_context: bool = True,
) -> PipelineResult:
    """Process a TeX item through the pipeline (skips classification/scanning)."""
    # Lazy imports
    from vbagent.agents.content_generation.idea import extract_ideas
    from vbagent.agents.variants.variant import generate_variant
    from vbagent.models.classification import ClassificationResult
    from vbagent.models.pipeline import PipelineResult
    
    console = _get_console()
    
    # Create a minimal classification for TeX input
    classification = ClassificationResult(
        subject=get_config().subject,
        question_type="subjective",
        chapter="General",
        topic="physics",
        subtopic="general",
        has_diagram=False,
        num_options=None,
        key_concepts=[],
        requires_calculus=False,
        estimated_marks=4,
        time_estimate_minutes=3,
        confidence=1.0,
        classified_from="latex",
    )
    
    latex = tex_content
    
    # Extract problem and solution
    problem, solution = extract_problem_solution(latex)
    
    # Stage 4: Ideas (optional)
    ideas = None
    if generate_ideas and problem and solution:
        with console.status("[bold green]Extracting ideas..."):
            ideas = extract_ideas(problem, solution)
        # Display ideas in a formatted panel
        ideas_text = f"[bold]Concepts:[/bold] {', '.join(ideas.concepts)}\n"
        ideas_text += f"[bold]Formulas:[/bold] {', '.join(ideas.formulas)}\n"
        ideas_text += f"[bold]Techniques:[/bold] {', '.join(ideas.techniques)}\n"
        ideas_text += f"[bold]Difficulty Factors:[/bold] {', '.join(ideas.difficulty_factors)}"
        console.print(_get_panel(ideas_text, title="Extracted Ideas", border_style="yellow"))
    
    # Stage 5: Alternates (optional)
    alternate_solutions = []
    if generate_alternate and problem and solution:
        with console.status("[bold green]Generating alternate solution..."):
            alt = generate_alternate_solution(problem, solution, ideas)
            alternate_solutions.append(alt)
        console.print(_get_panel(alt, title="Alternate Solution", border_style="magenta"))
    
    # Stage 6: Variants (optional)
    variants = {}
    for vtype in variant_types:
        with console.status(f"[bold green]Generating {vtype} variant..."):
            variant_latex = generate_variant(latex, vtype, ideas, use_context=use_context)
            variants[vtype] = variant_latex
        console.print(_get_panel(variant_latex, title=f"{vtype.title()} Variant", border_style="green"))
    
    return PipelineResult(
        source_path=source_path,
        classification=classification,
        latex=latex,
        tikz_code=None,
        ideas=ideas,
        alternate_solutions=alternate_solutions,
        variants=variants,
    )


def generate_alternate_solution(problem: str, solution: str, ideas) -> str:
    """Generate an alternate solution using the alternate agent."""
    from vbagent.agents.content_generation.alternate import generate_alternate
    return generate_alternate(problem, solution, ideas)



def process_generated_problem(
    generated: "GeneratedProblem",
    problem_num: int,
    output_base_dir: Path = Path("agentic")
) -> dict:
    """Process a generated problem through the full pipeline.
    
    Runs the complete workflow on a problem generated by Agent 5:
    1. Generate TikZ from diagram_description (if present)
    2. Run Agent 4 (LaTeX Classifier) on the problem
    3. Run Agent 2 (Diagram Analyzer) if has_diagram
    4. Run Agent 3 (Difficulty Assessor)
    5. Merge metadata into LaTeX
    6. Save everything in standard format
    
    Args:
        generated: GeneratedProblem from Agent 5
        problem_num: Problem number for file naming
        output_base_dir: Base directory for output (default: agentic/)
        
    Returns:
        Dictionary with paths and metadata
    """
    from vbagent.agents.classification.latex_classifier import classify_from_latex
    from vbagent.agents.classification.diagram_analyzer import analyze_diagram_from_description
    from vbagent.agents.classification.difficulty_assessor import assess_difficulty
    from vbagent.agents.diagram.tikz import generate_tikz
    from vbagent.models.classification import GeneratedProblem
    import json
    
    console = _get_console()
    
    # Create output directories
    dirs = {
        "generated": output_base_dir / "generated",
        "classifications": output_base_dir / "classifications",
        "diagrams": output_base_dir / "diagrams",
        "difficulty": output_base_dir / "difficulty",
        "tikz": output_base_dir / "tikz",
    }
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    problem_name = f"problem_{problem_num}"
    
    # Step 1: Generate TikZ if diagram_description exists
    tikz_code = None
    if generated.diagram_description:
        console.print(f"[cyan]→ Generating TikZ from description...[/cyan]")
        try:
            tikz_code = generate_tikz(
                description=generated.diagram_description,
                use_context=True
            )
            # Save TikZ
            tikz_file = dirs["tikz"] / f"{problem_name}.tex"
            tikz_file.write_text(tikz_code)
            console.print(f"[green]✓ TikZ saved to {tikz_file}[/green]")
            
            # Insert TikZ into problem if it has \input{diagram}
            if r'\input{diagram}' in generated.problem_latex:
                generated.problem_latex = insert_tikz_into_latex(generated.problem_latex, tikz_code)
        except Exception as e:
            console.print(f"[yellow]! TikZ generation failed: {e}[/yellow]")
    
    # Step 2: Run Agent 4 (LaTeX Classifier)
    console.print(f"[cyan]→ Classifying generated problem...[/cyan]")
    primary = classify_from_latex(generated.problem_latex)
    
    # Save classification
    classification_file = dirs["classifications"] / f"{problem_name}.json"
    classification_file.write_text(json.dumps(primary.model_dump(), indent=2))
    console.print(f"[green]✓ Classification saved[/green]")
    
    # Step 3: Run Agent 2 (Diagram Analyzer) if has_diagram
    diagram = None
    if primary.has_diagram or generated.diagram_description:
        console.print(f"[cyan]→ Analyzing diagram...[/cyan]")
        try:
            # Use description-based analysis since we don't have an image
            from vbagent.agents.classification.diagram_analyzer import analyze_diagram_from_description
            diagram = analyze_diagram_from_description(
                description=generated.diagram_description or "Generated diagram",
                primary=primary
            )
            # Save diagram analysis
            diagram_file = dirs["diagrams"] / f"{problem_name}.json"
            diagram_file.write_text(json.dumps(diagram.model_dump(), indent=2))
            console.print(f"[green]✓ Diagram analysis saved[/green]")
        except Exception as e:
            console.print(f"[yellow]! Diagram analysis failed: {e}[/yellow]")
    
    # Step 4: Run Agent 3 (Difficulty Assessor)
    console.print(f"[cyan]→ Assessing difficulty...[/cyan]")
    difficulty = assess_difficulty(
        latex_content=generated.problem_latex + "\n\n" + generated.solution_latex,
        primary=primary,
        diagram=diagram
    )
    
    # Save difficulty assessment
    difficulty_file = dirs["difficulty"] / f"{problem_name}.json"
    difficulty_file.write_text(json.dumps(difficulty.model_dump(), indent=2))
    console.print(f"[green]✓ Difficulty assessment saved[/green]")
    
    # Step 5: Merge metadata into LaTeX
    console.print(f"[cyan]→ Merging metadata...[/cyan]")
    latex_with_metadata = merge_metadata_into_latex(
        latex=generated.problem_latex,
        primary=primary,
        diagram=diagram,
        difficulty=difficulty
    )
    
    # Step 6: Save final problem with metadata
    problem_file = dirs["generated"] / f"{problem_name}.tex"
    problem_file.write_text(latex_with_metadata)
    console.print(f"[green]✓ Problem saved to {problem_file}[/green]")
    
    # Also save solution and idea separately
    solution_file = dirs["generated"] / f"{problem_name}_solution.tex"
    solution_file.write_text(generated.solution_latex)
    
    idea_file = dirs["generated"] / f"{problem_name}_idea.tex"
    idea_file.write_text(generated.idea_latex)
    
    return {
        "problem_path": str(problem_file),
        "solution_path": str(solution_file),
        "idea_path": str(idea_file),
        "tikz_path": str(dirs["tikz"] / f"{problem_name}.tex") if tikz_code else None,
        "classification": primary.model_dump(),
        "diagram_analysis": diagram.model_dump() if diagram else None,
        "difficulty": difficulty.model_dump(),
    }
