"""Conceptual-plus MCQ variant with auxiliary concepts and calculus flavor (embedded)."""

PROMPT = r"""
## Overall Task & Output Format

**Goal:** Create a deep, thoughtful MCQ variant that keeps the original problem’s core topic central while deliberately blending in 1–2 auxiliary concepts (from related topics). Wherever reasonable, shift the formulation toward a calculus-based treatment (e.g., time/space dependent quantities, integration/differentiation, rates of change, optimization). Change context and numerical values; the underlying idea may evolve, but the core topic must remain primary.

**CRITICAL OUTPUT CONSTRAINT:** Return only the raw LaTeX snippet, starting exactly with `\item` and ending exactly after `\end{solution}`. No preamble, no `\documentclass`, no `\begin{document}`, no extra commentary.

---

## Construction Requirements

1. **Identify the core topic and keep it central** (e.g., kinematics, work–energy, circular motion, oscillations, electrostatics, thermodynamics). State it implicitly through the problem you write; do not label it explicitly.
2. **Blend with 1–2 auxiliary concepts** that deepen the reasoning (e.g., small-angle approximation, energy dissipation, variable forces, geometry/constraints, continuity, simple circuit relations, fluid pressure, etc.).
3. **Prefer calculus where appropriate**:
   - Replace constants with functions such as $a(t)$, $F(x)$, $E(r)$, or a parameter varying smoothly in time/space.
   - Use single-variable integrals/derivatives that are solvable in closed form; avoid unsolved differential equations.
   - If relevant, include an extremum/optimization step or a rate-of-change interpretation.
4. **Change numerical values and context** to be realistic, dimensionally consistent, and different from the original.
5. **Produce a complete MCQ with one correct option** and three plausible distractors consistent with the new model and numbers.
6. **Prefer integer‑friendly values** so that key intermediate results and the final answer are integers (or simple rationals) to keep arithmetic simple while emphasizing the core idea.

---

## Required LaTeX Structure

1. **Problem (`\item ...`)**
   - Begin immediately with `\item`.
   - State the new conceptual-plus question, keeping the core topic central and weaving in the auxiliary concept(s).
   - Use inline math `$...$` for all symbols and quantities.

2. **Optional diagram** in `\begin{center}\begin{tikzpicture}...\end{tikzpicture}\end{center}` if it clarifies geometry/fields/forces.

3. **Options (`\begin{tasks}(2) ... \end{tasks}`)**
   - Provide four options via `\task`.
   - Append ` \ans` to the single correct option.

4. **Solution (`\begin{solution} ... \end{solution}`)**
   - Use an `align*` environment, one logical step per line.
   - Incorporate the calculus step(s) cleanly (e.g., an integral of $a(t)$ to get $v(t)$, work via $\int F(x)\,dx$, charge via $\int i(t)\,dt$, flux via an area integral if simple, etc.).
   - Use `\intertext{...}` sparingly to explain ideas between lines; keep math inside `$...$`.
   - End with a clear statement: “Therefore, the correct option is (x).”
   - No blank lines inside `align*`.

---

## Strict Formatting Rules

* Inline math only: `$...$` everywhere (no display math fences).
* Use macros with braces: `\vec{a}`, `\frac{a}{b}`, `\hat{i}`, `\text{m}`.
* Parentheses/Brackets: `\left(\cdot\right)`, `\left[\cdot\right]`, `\left|\cdot\right|`.
* Units with proper spacing: `\ \text{m}`, `\ \text{s}`, `\ \text{N}`, `\ \text{J}`.
* Exactly one correct option, marked with `\ans`.

---

## Quality Checklist (silently ensure)

* Core topic is unmistakably central; auxiliary concept(s) enrich but do not overshadow it.
* Calculus step is necessary, correct, and solvable cleanly.
* Numbers are realistic and dimensionally consistent; final numeric values match the marked option.
* Options are coherent with the model (no impossible magnitudes/signs).
* The output begins with `\item` and ends right after `\end{solution}`.
"""

__all__ = ["PROMPT"]

