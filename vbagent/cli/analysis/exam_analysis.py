"""CLI command for exam analysis and concept aggregation."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from vbagent.analysis.extractor import scan_problem_directory
from vbagent.analysis.matcher import (
    load_syllabus,
    match_problems_to_syllabus,
    aggregate_ideas_by_topic,
)
from vbagent.analysis.generator import generate_analysis_latex
from vbagent.agents.analysis.concept_organizer import organize_concepts


@click.command()
@click.option('--chapter', required=True, help='Chapter name (e.g., "KINEMATICS")')
@click.option('--exam', type=click.Choice(['jee_main', 'neet', 'jee_advanced']), 
              default='jee_main', help='Exam type')
@click.option('--year', type=int, default=2026, help='Exam year')
@click.option('--subject', type=click.Choice(['physics', 'chemistry', 'mathematics', 'biology']),
              default='physics', help='Subject')
@click.option('--input-dir', type=click.Path(exists=True), default='agentic/scans',
              help='Directory with problem files')
@click.option('-o', '--output', type=click.Path(), default='analysis.tex',
              help='Output LaTeX file')
@click.option('--no-cache', is_flag=True, help='Force regeneration without using cache')
def analysis(
    chapter: str,
    exam: str,
    year: int,
    subject: str,
    input_dir: str,
    output: str,
    no_cache: bool,
):
    """Generate exam analysis with topic-wise concept aggregation.
    
    Analyzes problems from a chapter, extracts key concepts, formulas, and
    techniques, then generates a comprehensive LaTeX document with:
    
    - Syllabus coverage with problem references
    
    - Topic-wise concept breakdown
    
    - All problems in two-column format
    
    \b
    Examples:
        vbagent exam analysis --chapter "KINEMATICS" --exam jee_main --year 2026
        vbagent exam analysis --chapter "ELECTROSTATICS" --exam neet -o electro.tex
    """
    console = Console()
    
    try:
        # Step 1: Scan problem directory
        console.print(f"[cyan]Scanning problems from:[/cyan] {input_dir}")
        input_path = Path(input_dir)
        problems = scan_problem_directory(input_path)
        
        if not problems:
            console.print("[red]No problem files found![/red]")
            return
        
        console.print(f"[green]Found {len(problems)} problem(s)[/green]")
        
        # Step 2: Load syllabus
        console.print(f"[cyan]Loading syllabus:[/cyan] {exam}/{subject}")
        syllabus = load_syllabus(exam, subject)
        
        # Step 3: Get chapter data from syllabus
        console.print(f"[cyan]Preparing analysis for chapter:[/cyan] {chapter}")
        
        # Check if chapter is a number
        if chapter.isdigit():
            chapter_num = int(chapter)
            chapters_list = list(syllabus.keys())
            
            if 1 <= chapter_num <= len(chapters_list):
                actual_chapter_name = chapters_list[chapter_num - 1]
                chapter_info = syllabus[actual_chapter_name]
                console.print(f"[dim]Using chapter {chapter_num}: {actual_chapter_name}[/dim]")
            else:
                console.print(f"[red]Chapter number {chapter_num} out of range![/red]")
                console.print(f"[yellow]Valid range: 1-{len(chapters_list)}[/yellow]")
                console.print("[yellow]Available chapters:[/yellow]")
                for i, ch in enumerate(chapters_list, 1):
                    console.print(f"  {i}. {ch}")
                return
        else:
            # Find matching chapter by name (case-insensitive)
            chapter_upper = chapter.upper()
            actual_chapter_name = None
            chapter_info = None
            
            for ch_name, ch_data in syllabus.items():
                if chapter_upper in ch_name.upper() or ch_name.upper() in chapter_upper:
                    actual_chapter_name = ch_name
                    chapter_info = ch_data
                    break
            
            if not actual_chapter_name:
                console.print(f"[red]Chapter '{chapter}' not found in syllabus![/red]")
                console.print("[yellow]Available chapters:[/yellow]")
                for i, ch in enumerate(syllabus.keys(), 1):
                    console.print(f"  {i}. {ch}")
                return
        
        # Get syllabus topics for this chapter
        syllabus_topics = chapter_info.get('topics', [])
        
        # Step 4: Extract ideas from ALL problems
        console.print(f"[cyan]Extracting ideas from {len(problems)} problem(s)...[/cyan]")
        
        # Prepare full problem data for agent - include ALL problems
        all_problems = []
        for problem in problems:
            problem_data = {
                'problem_num': problem['number'],
                'question': problem.get('question', ''),
                'solution': problem.get('solution', ''),
                'concepts': problem.get('ideas', {}).get('concepts', []),
                'formulas': problem.get('ideas', {}).get('formulas', []),
                'techniques': problem.get('ideas', {}).get('techniques', [])
            }
            all_problems.append(problem_data)
        
        console.print(f"[green]Extracted data from {len(all_problems)} problem(s)[/green]")
        
        # Step 5: Organize concepts using AI agent
        console.print("[cyan]Organizing concepts with AI agent...[/cyan]")
        
        import time
        t_start = time.time()
        
        # Run agent to organize concepts
        aggregated_ideas = organize_concepts(
            raw_ideas={'all_problems': {'problems': all_problems}},  # Send all problem data
            syllabus_topics=syllabus_topics,
            chapter_name=actual_chapter_name,
            exam=exam,
            subject=subject,
            show_spinner=True,
            no_cache=no_cache,
        )
        
        elapsed = time.time() - t_start
        console.print(f"[green]✓ Concepts organized in {elapsed:.1f}s[/green]")
        
        # Step 6: Generate LaTeX
        console.print("[cyan]Generating LaTeX document...[/cyan]")
        
        # Load template to get note
        from vbagent.analysis.templates import load_chapter_template
        template = load_chapter_template(exam, subject, actual_chapter_name)
        chapter_note = template.get('note') if template else None
        
        # Build matched_data structure for generator
        matched_data = {
            actual_chapter_name: {
                'topics': [{'topic': t, 'problems': []} for t in syllabus_topics],
                'all_problems': [p['number'] for p in problems],
                'description': chapter_info.get('description', ''),
            }
        }
        
        latex_content = generate_analysis_latex(
            matched_data=matched_data,
            aggregated_ideas=aggregated_ideas,
            exam=exam.replace('_', ' ').title(),
            year=year,
            subject=subject,
            chapter_name=actual_chapter_name,
            num_problems=len(problems),
            chapter_note=chapter_note
        )
        
        # Step 7: Write output
        output_path = Path(output)
        output_path.write_text(latex_content, encoding='utf-8')
        
        console.print(f"\n[green]✓ Analysis complete![/green]")
        console.print(f"[cyan]Output:[/cyan] {output_path}")
        console.print(f"\n[dim]Summary:[/dim]")
        console.print(f"  • Chapter: {actual_chapter_name}")
        console.print(f"  • Problems analyzed: {len(problems)}")
        console.print(f"  • Problems with data: {len(all_problems)}")
        console.print(f"  • Topics in syllabus: {len(syllabus_topics)}")
        
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Analysis failed:[/red] {e}")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
