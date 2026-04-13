"""CLI command to view syllabus information."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from vbagent.analysis.matcher import load_syllabus


@click.command()
@click.option('--exam', type=click.Choice(['jee_main', 'neet', 'jee_advanced']), 
              help='Exam type (if not specified, shows all)')
@click.option('--subject', type=click.Choice(['physics', 'chemistry', 'mathematics', 'biology']),
              default='physics', help='Subject')
@click.option('--chapter', help='Show topics for a specific chapter')
def syllabus(exam: str, subject: str, chapter: str):
    """View syllabus information for exams.
    
    Shows available chapters and topics for JEE Main, NEET, and JEE Advanced.
    
    \b
    Examples:
        vbagent analysis syllabus                           # List all chapters
        vbagent analysis syllabus --exam jee_main          # JEE Main chapters
        vbagent analysis syllabus --chapter "KINEMATICS"   # Topics in chapter
    """
    console = Console()
    
    # Determine which exams to show
    if exam:
        exams_to_show = [exam]
    else:
        # Check which exam syllabi exist
        exams_to_show = []
        syllabus_dir = Path(__file__).parent.parent.parent / 'data' / 'syllabus'
        for exam_dir in syllabus_dir.iterdir():
            if exam_dir.is_dir():
                exam_file = exam_dir / f'{subject}.json'
                if exam_file.exists():
                    exams_to_show.append(exam_dir.name)
    
    if not exams_to_show:
        console.print(f"[red]No syllabus found for {subject}[/red]")
        return
    
    # Show syllabus for each exam
    for exam_name in exams_to_show:
        try:
            syllabus_data = load_syllabus(exam_name, subject)
            
            exam_display = exam_name.replace('_', ' ').title()
            console.print(f"\n[bold cyan]{exam_display} - {subject.capitalize()}[/bold cyan]\n")
            
            if chapter:
                # Show topics for specific chapter
                _show_chapter_topics(console, syllabus_data, chapter)
            else:
                # Show all chapters
                _show_all_chapters(console, syllabus_data)
                
        except FileNotFoundError:
            console.print(f"[yellow]Syllabus not found for {exam_name}/{subject}[/yellow]")


def _show_all_chapters(console: Console, syllabus_data: dict):
    """Show all chapters in a table."""
    table = Table(show_header=True, header_style="bold magenta", show_lines=False)
    table.add_column("#", style="cyan", width=3)
    table.add_column("Chapter", style="cyan", no_wrap=False)
    table.add_column("Topics", style="dim")
    table.add_column("Description", style="dim")
    
    for i, (chapter_name, chapter_data) in enumerate(syllabus_data.items(), 1):
        topics = chapter_data.get('topics', [])
        description = chapter_data.get('description', '')
        
        topic_count = f"{len(topics)} topics"
        
        table.add_row(
            str(i),
            chapter_name,
            topic_count,
            description[:50] + "..." if len(description) > 50 else description
        )
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(syllabus_data)} chapters[/dim]")
    console.print(f"[dim]Use --chapter \"CHAPTER_NAME\" or --chapter N to see topics[/dim]")


def _show_chapter_topics(console: Console, syllabus_data: dict, chapter_filter: str):
    """Show topics for a specific chapter."""
    # Check if chapter_filter is a number
    matched_chapter = None
    chapter_data = None
    
    if chapter_filter.isdigit():
        # User provided a chapter number
        chapter_num = int(chapter_filter)
        chapters_list = list(syllabus_data.items())
        
        if 1 <= chapter_num <= len(chapters_list):
            matched_chapter, chapter_data = chapters_list[chapter_num - 1]
        else:
            console.print(f"[red]Chapter number {chapter_num} out of range![/red]")
            console.print(f"[yellow]Valid range: 1-{len(chapters_list)}[/yellow]")
            return
    else:
        # Find matching chapter by name (case-insensitive)
        chapter_upper = chapter_filter.upper()
        
        for ch_name, ch_data in syllabus_data.items():
            if chapter_upper in ch_name.upper() or ch_name.upper() in chapter_upper:
                matched_chapter = ch_name
                chapter_data = ch_data
                break
    
    if not matched_chapter:
        console.print(f"[red]Chapter '{chapter_filter}' not found![/red]")
        console.print("\n[yellow]Available chapters:[/yellow]")
        for i, ch in enumerate(syllabus_data.keys(), 1):
            console.print(f"  {i}. {ch}")
        return
    
    # Show chapter info
    console.print(f"[bold]{matched_chapter}[/bold]\n")
    
    description = chapter_data.get('description', '')
    if description:
        console.print(f"[dim]{description}[/dim]\n")
    
    # Show topics
    topics = chapter_data.get('topics', [])
    console.print(f"[cyan]Topics ({len(topics)}):[/cyan]\n")
    
    for i, topic in enumerate(topics, 1):
        console.print(f"  {i}. {topic}")
    
    # Get chapter number for display
    chapter_num = list(syllabus_data.keys()).index(matched_chapter) + 1
    
    console.print(f"\n[dim]Use this chapter with:[/dim]")
    console.print(f"[dim]  vbagent analysis generate --chapter {chapter_num}[/dim]")
    console.print(f"[dim]  vbagent analysis generate --chapter \"{matched_chapter}\"[/dim]")
