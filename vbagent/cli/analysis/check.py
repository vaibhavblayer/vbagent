"""CLI command for auditing and fixing revision sheets against the syllabus."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table


@click.command()
@click.option("--chapter", required=True, help='Chapter name (e.g., "GRAVITATION")')
@click.option("--exam", type=click.Choice(["jee_main", "neet", "jee_advanced"]),
              default="jee_main", help="Exam type")
@click.option("--subject", type=click.Choice(["physics", "chemistry", "mathematics", "biology"]),
              default="physics", help="Subject")
@click.option("-f", "--file", "tex_file", type=click.Path(exists=True),
              default="analysis.tex", help="Revision sheet .tex file to audit")
@click.option("--fix", is_flag=True, help="Auto-fix: remove extras, add missing topics, rewrite file")
def check(
    chapter: str,
    exam: str,
    subject: str,
    tex_file: str,
    fix: bool,
):
    """Audit a revision sheet against the syllabus.

    Checks for missing topics, extra (out-of-syllabus) ideas, and thin
    coverage. With --fix, automatically removes extras and generates
    content for missing topics.

    \b
    Examples:
        vbagent analysis check --chapter GRAVITATION -f revision.tex
        vbagent analysis check --chapter GRAVITATION -f revision.tex --fix
    """
    console = Console()

    try:
        from vbagent.analysis.matcher import load_syllabus
        from vbagent.agents.analysis.revision_checker import (
            audit_revision_sheet,
            extract_topics_from_tex,
            apply_fixes,
        )

        # 1. Load syllabus
        console.print(f"[cyan]Loading syllabus:[/cyan] {exam}/{subject}")
        syllabus = load_syllabus(exam, subject)

        # Resolve chapter name
        actual_chapter_name = None
        chapter_info = None
        if chapter.isdigit():
            chapters_list = list(syllabus.keys())
            idx = int(chapter) - 1
            if 0 <= idx < len(chapters_list):
                actual_chapter_name = chapters_list[idx]
                chapter_info = syllabus[actual_chapter_name]
        else:
            chapter_upper = chapter.upper()
            for ch_name, ch_data in syllabus.items():
                if chapter_upper in ch_name.upper() or ch_name.upper() in chapter_upper:
                    actual_chapter_name = ch_name
                    chapter_info = ch_data
                    break

        if not actual_chapter_name:
            console.print(f"[red]Chapter '{chapter}' not found in syllabus![/red]")
            return

        syllabus_topics = chapter_info.get("topics", [])
        console.print(f"[green]Chapter:[/green] {actual_chapter_name} ({len(syllabus_topics)} syllabus topics)")

        # 2. Read and parse the .tex file
        tex_path = Path(tex_file)
        tex_content = tex_path.read_text(encoding="utf-8")
        revision_topics = extract_topics_from_tex(tex_content)
        total_ideas = sum(len(v) for v in revision_topics.values())
        console.print(f"[green]Revision sheet:[/green] {len(revision_topics)} topics, {total_ideas} ideas")

        # 3. Run audit agent
        import time
        console.print("[cyan]Running syllabus audit...[/cyan]")
        t0 = time.time()

        report = audit_revision_sheet(
            syllabus_topics=syllabus_topics,
            revision_topics=revision_topics,
            chapter_name=actual_chapter_name,
            show_spinner=True,
        )

        elapsed = time.time() - t0
        console.print(f"[green]✓ Audit complete in {elapsed:.1f}s[/green]\n")

        # 4. Display report
        table = Table(title=f"Syllabus Audit: {actual_chapter_name}")
        table.add_column("Status", style="bold", width=10)
        table.add_column("Details")

        covered_count = len(syllabus_topics) - len(report.missing)
        table.add_row("✅ Covered", f"{covered_count}/{len(syllabus_topics)} topics")

        if report.missing:
            missing_names = ", ".join(m.topic_name for m in report.missing)
            table.add_row("❌ Missing", missing_names)
        else:
            table.add_row("❌ Missing", "None")

        if report.thin:
            thin_items = ", ".join(f"{t.topic_name} ({t.idea_count} idea{'s' if t.idea_count != 1 else ''})" for t in report.thin)
            table.add_row("⚠️  Thin", thin_items)
        else:
            table.add_row("⚠️  Thin", "None")

        if report.extra:
            extra_items = ", ".join(f"{e.idea_title}" for e in report.extra)
            table.add_row("🚫 Extra", extra_items)
        else:
            table.add_row("🚫 Extra", "None")

        console.print(table)

        # 5. Apply fixes if requested
        if fix and (report.missing or report.extra):
            console.print("\n[cyan]Applying fixes...[/cyan]")

            fixed_content = apply_fixes(tex_content, report)
            tex_path.write_text(fixed_content, encoding="utf-8")

            changes = []
            if report.extra:
                changes.append(f"removed {len(report.extra)} extra idea(s)")
            if report.missing:
                changes.append(f"added {len(report.missing)} missing topic(s)")

            console.print(f"[green]✓ Fixed:[/green] {', '.join(changes)}")
            console.print(f"[cyan]Updated:[/cyan] {tex_path}")
        elif fix:
            console.print("\n[green]Nothing to fix — sheet is clean.[/green]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Check failed:[/red] {e}")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
