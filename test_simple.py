#!/usr/bin/env python3
"""Simple test for LaTeX classifier and difficulty assessor"""

from rich.console import Console

console = Console()

latex_content = r"""
A block of mass $5\,\text{kg}$ is placed on a rough horizontal surface with coefficient of friction $\mu = 0.3$. A horizontal force of $20\,\text{N}$ is applied on the block. Find the acceleration of the block. (Take $g = 10\,\text{m/s}^2$)

\begin{tasks}(4)
\task $1\,\text{m/s}^2$
\task $2\,\text{m/s}^2$
\task $3\,\text{m/s}^2$
\task $4\,\text{m/s}^2$
\end{tasks}
"""

console.print("\n[bold cyan]Testing LaTeX Classifier (Agent 4)[/bold cyan]\n")

from vbagent.agents.classification import classify_from_latex

result = classify_from_latex(latex_content, subject="physics")

console.print(f"✅ [green]Classification successful![/green]")
console.print(f"   Subject: {result.subject}")
console.print(f"   Type: {result.question_type}")
console.print(f"   Topic: {result.topic}")
console.print(f"   Concepts: {', '.join(result.key_concepts[:3])}")

console.print("\n[bold cyan]Testing Difficulty Assessor (Agent 3)[/bold cyan]\n")

from vbagent.agents.classification import assess_difficulty

difficulty = assess_difficulty(latex_content, result, None)

console.print(f"✅ [green]Difficulty assessment successful![/green]")
console.print(f"   Difficulty: {difficulty.difficulty} ({difficulty.difficulty_score}/10)")
console.print(f"   Time: {difficulty.expected_solve_time_minutes} minutes")
console.print(f"   Cognitive Level: {difficulty.cognitive_level}")
console.print(f"   Prerequisites: {', '.join(difficulty.prerequisite_concepts[:2])}")

console.print("\n[bold green]✅ All tests passed![/bold green]\n")
