"""CLI command for generating problem variants.

Generates different types of physics problem variants:
- numerical: Modify only numerical values
- context: Modify only the scenario/context
- conceptual: Modify the core physics concept
- calculus: Add calculus-based modifications
- multi: Combine multiple problems
"""

import json
from pathlib import Path
from typing import Optional

import click

from vbagent.tex import parse_tex_file, extract_items
from ..common import _get_console, _get_panel


def extract_items_from_tex(content: str) -> list[str]:
    """Extract individual items from a TeX file."""
    return extract_items(content)


def filter_items_by_range(
    items: list[str],
    item_range: Optional[tuple[int, int]],
) -> list[str]:
    """Filter items by the specified range."""
    if not item_range:
        return items
    start, end = item_range
    start_idx = max(0, start - 1)
    end_idx = min(len(items), end)
    return items[start_idx:end_idx]


def load_ideas(ideas_path: str, idea_result_cls):
    """Load ideas from a JSON file."""
    try:
        content = Path(ideas_path).read_text()
        data = json.loads(content)
        return idea_result_cls(**data)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return None


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-i", "--image",
    type=click.Path(exists=True),
    help="Image file path (will be scanned first)"
)
@click.option(
    "-t", "--tex",
    type=click.Path(exists=True),
    help="TeX file path containing problem(s)"
)
@click.option(
    "--type", "variant_type",
    required=True,
    type=click.Choice(["numerical", "context", "conceptual", "calculus", "cross_topic", "multi"]),
    help="Type of variant to generate"
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
    help="[DEPRECATED] Use --from and --to instead. Range of items to process (1-based inclusive)"
)
@click.option(
    "-n", "--count",
    default=1,
    type=int,
    help="Number of variants to generate per problem (default: 1)"
)
@click.option(
    "--context", "context_files",
    multiple=True,
    type=click.Path(exists=True),
    help="Additional context files for multi variant (can be used multiple times)"
)
@click.option(
    "--ideas",
    type=click.Path(exists=True),
    help="Path to ideas JSON file for context"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output TeX file path for saving results"
)
@click.option(
    "-c", "--compile", "do_compile",
    is_flag=True,
    help="Compile variants to validate; retry with agent on failure"
)
@click.option(
    "--verbose-compile", "verbose_compile",
    is_flag=True,
    help="Show full LaTeX document + preamble before each compile and prompt to continue/skip/quit"
)
def variant(
    image: Optional[str],
    tex: Optional[str],
    variant_type: str,
    from_index: Optional[int],
    to_index: Optional[int],
    item: Optional[int],
    item_range: Optional[tuple[int, int]],
    count: int,
    context_files: tuple[str, ...],
    ideas: Optional[str],
    output: Optional[str],
    do_compile: bool,
    verbose_compile: bool,
):
    """Generate problem variants.
    
    Creates variants of physics problems with controlled modifications.
    
    \b
    Variant Types:
        numerical    - Change only numbers, keep context
        context      - Change scenario, keep numbers
        conceptual   - Change physics concept
        calculus     - Add calculus elements
        cross_topic  - Integrate a complementary physics topic (multi-stage)
        multi        - Combine multiple problems
    
    \b
    Examples:
        vbagent variant -t problem.tex --type numerical
        vbagent variant --tex problem.tex --type numerical --count 3
        vbagent variant -t problem.tex --type context -o variants.tex
        vbagent variant -t problem.tex --type cross_topic
        vbagent variant -t problems.tex --type numerical --from 1 --to 5
        vbagent variant -t problems.tex --type numerical --item 3
        vbagent variant --type multi --context p1.tex --context p2.tex -o combined.tex
        vbagent variant -i image.png --type numerical --output variant.tex
    """
    # Lazy imports - only load heavy dependencies when command runs
    from vbagent.agents.variants.variant import generate_variant as gen_variant
    from vbagent.agents.variants.multi_context_variant import generate_multi_context_variant
    from vbagent.agents.classifier import classify
    from vbagent.agents.content_generation.scanner import scan
    from vbagent.models.content import IdeaResult
    
    # Compile helper (lazy, only if -c)
    def maybe_compile(latex_content: str) -> str:
        if not do_compile:
            return latex_content
        from vbagent.compile import compile_and_retry
        from vbagent.agents.quality.latex_fixer import fix_latex
        from vbagent.config import get_config
        subject = get_config().subject
        console.print("[dim]  → Compiling variant...[/dim]")
        fixed, _ = compile_and_retry(latex_content, retry_fn=fix_latex, subject=subject, console=console, verbose=verbose_compile)
        return fixed
    
    console = _get_console()
    
    # Show deprecation warning
    import sys
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
    
    # Convert to tuple for internal use
    if from_index or to_index:
        item_range = (from_index or 1, to_index or 999999)
    
    try:
        # Validate input
        if variant_type == "multi":
            if not context_files and not tex:
                console.print(
                    "[red]Error:[/red] Multi variant requires --context files or --tex"
                )
                raise SystemExit(1)
        else:
            if not image and not tex:
                console.print(
                    "[red]Error:[/red] Either --image or --tex is required"
                )
                raise SystemExit(1)
        
        # Load ideas if provided
        ideas_result = load_ideas(ideas, IdeaResult) if ideas else None
        if ideas and not ideas_result:
            console.print(f"[yellow]Warning:[/yellow] Could not load ideas from {ideas}")
        
        all_variants = []
        
        if variant_type == "multi":
            # Handle multi-context variant
            source_problems = []
            
            if tex:
                content = parse_tex_file(tex)
                items = extract_items_from_tex(content)
                items = filter_items_by_range(items, item_range)
                source_problems.extend(items)
            
            for ctx_file in context_files:
                ctx_content = parse_tex_file(ctx_file)
                source_problems.append(ctx_content)
            
            if not source_problems:
                console.print("[red]Error:[/red] No source problems found")
                raise SystemExit(1)
            
            console.print(f"[cyan]Combining {len(source_problems)} problems...[/cyan]")
            
            for i in range(count):
                with console.status(f"[bold green]Generating multi-context variant {i + 1}/{count}..."):
                    result = generate_multi_context_variant(source_problems)
                    result = maybe_compile(result)
                    all_variants.append(result)
                
                console.print(_get_panel(
                    result,
                    title=f"Multi-Context Variant {i + 1}",
                    border_style="green"
                ))
        else:
            # Handle single-problem variants
            source_latex = ""
            classification_result = None
            
            if image:
                with console.status("[bold green]Scanning image..."):
                    classification = classify(image)
                    scan_result = scan(image, classification)
                    source_latex = scan_result.latex
                    classification_result = classification
                console.print(f"[cyan]Scanned image: {classification.question_type}[/cyan]")
            elif tex:
                content = parse_tex_file(tex)
                items = extract_items_from_tex(content)
                items = filter_items_by_range(items, item_range)
                
                if not items:
                    source_latex = content
                else:
                    for idx, item in enumerate(items, 1):
                        console.print(f"\n[cyan]Processing item {idx}/{len(items)}...[/cyan]")
                        
                        for i in range(count):
                            with console.status(f"[bold green]Generating {variant_type} variant {i + 1}/{count}..."):
                                result = gen_variant(item, variant_type, ideas_result)
                                result = maybe_compile(result)
                                all_variants.append(result)
                            
                            console.print(_get_panel(
                                result,
                                title=f"Item {idx} - {variant_type.title()} Variant {i + 1}",
                                border_style="green"
                            ))
                    
                    source_latex = ""
            
            if source_latex:
                for i in range(count):
                    with console.status(f"[bold green]Generating {variant_type} variant {i + 1}/{count}..."):
                        result = gen_variant(source_latex, variant_type, ideas_result, classification=classification_result)
                        result = maybe_compile(result)
                        all_variants.append(result)
                    
                    console.print(_get_panel(
                        result,
                        title=f"{variant_type.title()} Variant {i + 1}",
                        border_style="green"
                    ))
        
        # Save to file if output path specified
        if output and all_variants:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            combined = "\n\n% --- Variant ---\n\n".join(all_variants)
            output_path.write_text(combined)
            console.print(f"\n[green]Results saved to:[/green] {output}")
        
        if not all_variants:
            console.print("[yellow]No variants generated[/yellow]")
            
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Variant generation failed:[/red] {e}")
        raise SystemExit(1)
