"""LaTeX compilation and validation for generated content.

Wraps generated LaTeX snippets in a standalone document with all required
packages, compiles with pdflatex, and parses errors for agent retry.

Usage:
    from vbagent.compile import compile_latex, CompileResult

    result = compile_latex(latex_snippet, subject="physics")
    if not result.success:
        print(result.error_summary)  # Send to agent for retry
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CompileResult:
    """Result of a LaTeX compilation attempt."""
    success: bool
    error_summary: str = ""      # Short error for agent retry prompt
    log_output: str = ""         # Full pdflatex log
    pdf_path: Optional[str] = None  # Path to PDF if successful


# Preamble template for standalone compilation.
# Uses standalone class with preview for minimal overhead.
# Includes all packages that agents are told to use in prompts.
PREAMBLE_TEMPLATE = r"""\documentclass[preview, border=2mm]{{standalone}}

% --- Math ---
\usepackage{{amsmath, amssymb, amsthm, mathtools}}

% --- TikZ core + libraries ---
\usepackage{{tikz}}
\usetikzlibrary{{
    calc,
    decorations.pathmorphing,
    decorations.markings,
    patterns,
    arrows.meta,
    positioning,
    shapes.geometric,
    intersections,
    angles,
    quotes
}}

% --- Circuits ---
\usepackage[american]{{circuitikz}}

% --- Plots ---
\usepackage{{pgfplots}}
\pgfplotsset{{compat=1.18}}

% --- Tasks (MCQ options) ---
\usepackage{{tasks}}

% --- Solution environment ---
\newenvironment{{solution}}{{\par\textbf{{Solution:}}\par}}{{}}

% --- Answer marker ---
\newcommand{{\ans}}{{\ensuremath{{\checkmark}}}}

% --- Chemistry (if needed) ---
{chemistry_packages}

% --- KinemaTikZ stub (if not installed, define no-ops) ---
\IfFileExists{{kinematikz.sty}}{{%
    \usepackage{{kinematikz}}
}}{{%
    % Stub: define frame pic if kinematikz not available
}}

% --- tzplot stub ---
\IfFileExists{{tzplot.sty}}{{%
    \usepackage{{tzplot}}
}}{{}}

% --- Enumerate/itemize for biology ---
\usepackage{{enumitem}}

\begin{{document}}
{content}
\end{{document}}
"""


def _get_chemistry_packages(subject: str) -> str:
    """Get chemistry-specific package lines."""
    if subject == "chemistry":
        return (
            "\\usepackage[version=4]{mhchem}\n"
            "\\usepackage{chemfig}\n"
        )
    return ""


def _build_document(latex_snippet: str, subject: str = "physics") -> str:
    """Wrap a LaTeX snippet in a compilable standalone document.

    Args:
        latex_snippet: Raw LaTeX content (e.g. \\item ... \\end{solution})
        subject: Subject for package selection

    Returns:
        Complete LaTeX document string
    """
    chemistry_packages = _get_chemistry_packages(subject)

    # If snippet starts with \item, wrap in a list
    content = latex_snippet.strip()
    if content.startswith("\\item"):
        content = f"\\begin{{enumerate}}\n{content}\n\\end{{enumerate}}"

    return PREAMBLE_TEMPLATE.format(
        chemistry_packages=chemistry_packages,
        content=content,
    )


def _parse_errors(log: str) -> str:
    """Extract meaningful error lines from pdflatex log.

    Returns a concise summary suitable for sending back to an agent.
    """
    errors = []
    lines = log.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("!"):
            # Grab the error line and up to 2 context lines
            snippet = [line]
            for j in range(1, 4):
                if i + j < len(lines):
                    snippet.append(lines[i + j])
            errors.append("\n".join(snippet))

    if not errors:
        # Fallback: look for "LaTeX Error" or "Undefined control sequence"
        for line in lines:
            if "Error" in line or "Undefined" in line:
                errors.append(line.strip())

    if not errors:
        return "Compilation failed (unknown error — check log)"

    # Limit to first 5 errors
    return "\n\n".join(errors[:5])



def compile_latex(
    latex_snippet: str,
    subject: str = "physics",
    output_dir: Optional[str] = None,
    timeout: int = 30,
    verbose: bool = False,
) -> CompileResult:
    """Compile a LaTeX snippet to validate it.

    Creates a temp directory, writes a standalone document, runs pdflatex,
    and returns the result.

    Args:
        latex_snippet: Raw LaTeX content to validate
        subject: Subject for package selection (physics, chemistry, etc.)
        output_dir: If provided, copy PDF here on success
        timeout: pdflatex timeout in seconds
        verbose: If True, stream pdflatex output live to terminal

    Returns:
        CompileResult with success status and error details
    """
    # Check pdflatex is available
    if not shutil.which("pdflatex"):
        return CompileResult(
            success=False,
            error_summary="pdflatex not found. Install TeX Live or MacTeX.",
        )

    document = _build_document(latex_snippet, subject)

    with tempfile.TemporaryDirectory(prefix="vbagent_compile_") as tmpdir:
        tex_path = Path(tmpdir) / "compile_test.tex"
        tex_path.write_text(document)

        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory", tmpdir,
            str(tex_path),
        ]

        if verbose:
            # Stream output live to terminal, just like running pdflatex manually
            import sys
            print(f"\n$ {' '.join(cmd)}\n", flush=True)
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=tmpdir,
                )
                stdout_lines = []
                while True:
                    line = proc.stdout.readline()
                    if not line and proc.poll() is not None:
                        break
                    if line:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                        stdout_lines.append(line)
                proc.wait(timeout=timeout)
                stdout_text = "".join(stdout_lines)
                returncode = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                return CompileResult(
                    success=False,
                    error_summary="pdflatex timed out (possible infinite loop in TikZ)",
                )
        else:
            # Silent mode — capture everything
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir,
                )
                stdout_text = result.stdout
                returncode = result.returncode
            except subprocess.TimeoutExpired:
                return CompileResult(
                    success=False,
                    error_summary="pdflatex timed out (possible infinite loop in TikZ)",
                )

        log_path = Path(tmpdir) / "compile_test.log"
        log_output = log_path.read_text() if log_path.exists() else stdout_text

        pdf_path = Path(tmpdir) / "compile_test.pdf"

        if returncode == 0 and pdf_path.exists():
            final_pdf = None
            if output_dir:
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)
                final_pdf = str(out / "compile_test.pdf")
                shutil.copy2(pdf_path, final_pdf)

            return CompileResult(
                success=True,
                log_output=log_output,
                pdf_path=final_pdf,
            )
        else:
            error_summary = _parse_errors(log_output)
            return CompileResult(
                success=False,
                error_summary=error_summary,
                log_output=log_output,
            )




def compile_and_retry(
    latex_snippet: str,
    retry_fn,
    subject: str = "physics",
    max_retries: int = 2,
    console=None,
    verbose: bool = False,
) -> tuple[str, CompileResult]:
    """Compile LaTeX and retry with agent if it fails.

    Args:
        latex_snippet: The LaTeX content to validate
        retry_fn: Callable(error_summary, original_latex) -> new_latex
            Called when compilation fails, should return fixed LaTeX.
        subject: Subject for package selection
        max_retries: Maximum number of retry attempts
        console: Optional rich Console for status output
        verbose: If True, print full LaTeX document and preamble before
            each compile attempt and prompt user to continue/quit/skip.

    Returns:
        Tuple of (final_latex, final_compile_result)
    """
    current = latex_snippet

    for attempt in range(max_retries + 1):
        # In verbose mode, show the full document and prompt user
        if verbose and console:
            document = _build_document(current, subject)
            _show_compile_preview(console, document, current, attempt, max_retries)
            action = _prompt_compile_action(console)
            if action == "quit":
                console.print("[yellow]Compile aborted by user.[/yellow]")
                return current, CompileResult(
                    success=False,
                    error_summary="Compilation aborted by user.",
                )
            elif action == "skip":
                console.print("[dim]Skipping compilation, continuing...[/dim]")
                return current, CompileResult(
                    success=False,
                    error_summary="Compilation skipped by user.",
                )
            # action == "compile" → fall through

        result = compile_latex(current, subject=subject, verbose=verbose)

        if verbose and console and not result.success:
            console.print(
                f"\n[red bold]── Compile Error (attempt {attempt + 1}) ──[/red bold]"
            )
            console.print(result.error_summary)
            if result.log_output:
                # Show last 40 lines of log for context
                log_tail = "\n".join(result.log_output.splitlines()[-40:])
                from rich.panel import Panel
                from rich.syntax import Syntax
                console.print(Panel(
                    log_tail,
                    title="pdflatex log (last 40 lines)",
                    border_style="red",
                ))

        if result.success:
            if console and attempt > 0:
                console.print(
                    f"[green]  ✓ Compile passed (attempt {attempt + 1})[/green]"
                )
            elif console:
                console.print("[green]  ✓ Compile passed[/green]")
            return current, result

        if attempt < max_retries:
            if console:
                console.print(
                    f"[yellow]  ✗ Compile failed (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying...[/yellow]"
                )
            current = retry_fn(result.error_summary, current)
        else:
            if console:
                console.print(
                    f"[red]  ✗ Compile failed after {max_retries + 1} attempts[/red]"
                )

    return current, result



def _show_compile_preview(console, document: str, snippet: str, attempt: int, max_retries: int) -> None:
    """Print the full LaTeX document and preamble before compilation.

    Shows:
    - The complete .sty / preamble (everything before \\begin{document})
    - The content being compiled
    - The full document that pdflatex will receive
    """
    from rich.panel import Panel
    from rich.syntax import Syntax

    attempt_label = f"Attempt {attempt + 1}/{max_retries + 1}"

    # Split preamble and body for clarity
    doc_marker = r"\begin{document}"
    if doc_marker in document:
        idx = document.index(doc_marker)
        preamble = document[:idx].rstrip()
        body = document[idx:]
    else:
        preamble = ""
        body = document

    console.print(f"\n[bold cyan]{'═' * 60}[/bold cyan]")
    console.print(f"[bold cyan]  COMPILE PREVIEW  ({attempt_label})[/bold cyan]")
    console.print(f"[bold cyan]{'═' * 60}[/bold cyan]")

    # Show preamble (the "compile.sty" equivalent)
    console.print(Panel(
        Syntax(preamble, "latex", theme="monokai", line_numbers=True),
        title="[bold]Preamble / Packages (compile.sty equivalent)[/bold]",
        border_style="blue",
    ))

    # Show the LaTeX snippet being compiled
    console.print(Panel(
        Syntax(snippet, "latex", theme="monokai", line_numbers=True),
        title="[bold]LaTeX Snippet (your content)[/bold]",
        border_style="green",
    ))

    # Show the full document going to pdflatex
    console.print(Panel(
        Syntax(document, "latex", theme="monokai", line_numbers=True),
        title="[bold]Full Document → pdflatex[/bold]",
        border_style="yellow",
    ))


def _prompt_compile_action(console) -> str:
    """Prompt user to continue, skip, or quit compilation.

    Returns:
        One of: "compile", "skip", "quit"
    """
    console.print(
        "\n[bold]What would you like to do?[/bold]\n"
        "  [green](c)[/green] Continue to compile\n"
        "  [yellow](s)[/yellow] Skip compilation (continue without compiling)\n"
        "  [red](q)[/red] Quit\n"
    )
    while True:
        try:
            choice = input("Choice [c/s/q]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "quit"
        if choice in ("c", "compile", ""):
            return "compile"
        elif choice in ("s", "skip"):
            return "skip"
        elif choice in ("q", "quit"):
            return "quit"
        else:
            console.print("[dim]Please enter c, s, or q[/dim]")

