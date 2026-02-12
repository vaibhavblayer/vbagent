#!/usr/bin/env python3
"""Test script for multi-agent classification system"""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import json

console = Console()

# Test 1: LaTeX Classifier (Agent 4)
console.print("\n[bold cyan]═══ Test 1: LaTeX Classifier (Agent 4) ═══[/bold cyan]\n")

latex_content = r"""
A block of mass $5\,\text{kg}$ is placed on a rough horizontal surface with coefficient of friction $\mu = 0.3$. A horizontal force of $20\,\text{N}$ is applied on the block. Find the acceleration of the block. (Take $g = 10\,\text{m/s}^2$)

\begin{tasks}(4)
\task $1\,\text{m/s}^2$
\task $2\,\text{m/s}^2$
\task $3\,\text{m/s}^2$
\task $4\,\text{m/s}^2$
\end{tasks}
"""

from vbagent.agents.classification import classify_from_latex

console.print("[yellow]Classifying LaTeX content...[/yellow]")
result = classify_from_latex(latex_content, subject="physics")

console.print(Panel(
    f"[green]Subject:[/green] {result.subject}\n"
    f"[green]Type:[/green] {result.question_type}\n"
    f"[green]Chapter:[/green] {result.chapter}\n"
    f"[green]Topic:[/green] {result.topic}\n"
    f"[green]Subtopic:[/green] {result.subtopic}\n"
    f"[green]Has Diagram:[/green] {result.has_diagram}\n"
    f"[green]Key Concepts:[/green] {', '.join(result.key_concepts)}",
    title="[bold]Classification Result[/bold]",
    border_style="green"
))

# Test 2: Idea Generator (Agent 5)
console.print("\n[bold cyan]═══ Test 2: Idea Generator (Agent 5) ═══[/bold cyan]\n")

from vbagent.agents.classification import generate_from_idea

ideas = ["Newton's third law with collision between two objects"]
concepts = ["action-reaction pairs", "momentum conservation", "impulse"]
topic = "Laws of Motion"
console.print(f"[yellow]Generating problem from ideas:[/yellow] {', '.join(ideas)}")

generated = generate_from_idea(ideas, concepts, topic, difficulty="medium", subject="physics")

console.print(Panel(
    f"[green]Problem:[/green]\n{generated.problem_latex[:200]}...\n\n"
    f"[green]Solution:[/green]\n{generated.solution_latex[:200]}...\n\n"
    f"[green]Idea:[/green]\n{generated.idea_latex[:200]}...",
    title="[bold]Generated Problem[/bold]",
    border_style="green"
))

# Test 3: Difficulty Assessment (Agent 3)
console.print("\n[bold cyan]═══ Test 3: Difficulty Assessor (Agent 3) ═══[/bold cyan]\n")

from vbagent.agents.classification import assess_difficulty

console.print("[yellow]Assessing difficulty of LaTeX problem...[/yellow]")
difficulty = assess_difficulty(latex_content, result, None)

console.print(Panel(
    f"[green]Difficulty:[/green] {difficulty.difficulty} ({difficulty.difficulty_score}/10)\n"
    f"[green]Reasoning:[/green] {difficulty.difficulty_reasoning}\n\n"
    f"[green]Expected Time:[/green] {difficulty.expected_solve_time_minutes} minutes\n"
    f"[green]Cognitive Level:[/green] {difficulty.cognitive_level}\n\n"
    f"[green]Prerequisites:[/green]\n" + "\n".join(f"  • {p}" for p in difficulty.prerequisite_concepts) + "\n\n"
    f"[green]Common Mistakes:[/green]\n" + "\n".join(f"  • {m}" for m in difficulty.common_mistakes) + "\n\n"
    f"[green]Exam Relevance:[/green]\n"
    f"  Exam Type: {difficulty.exam_relevance.exam_type}\n"
    f"  Frequency: {difficulty.exam_relevance.frequency}\n"
    f"  Importance: {difficulty.exam_relevance.importance_score}/10",
    title="[bold]Difficulty Assessment[/bold]",
    border_style="green"
))

console.print("\n[bold green]✅ All tests completed successfully![/bold green]\n")
