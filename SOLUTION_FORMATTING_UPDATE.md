# Solution Formatting Update

## Changes Made

Updated solution generation prompts to match your exact formatting standards from `format_checker.py`.

## Key Formatting Rules Now Enforced

### 1. Solution Structure
```latex
\begin{solution}
\begin{align*}
\intertext{Brief explanation}
equation &= expression \\
        &= result
\end{align*}
\end{solution}
```

- `align*` directly inside `solution` (no other environments between)
- Use `\intertext{}` for text between equations
- Math within `\intertext{}` uses `$ ... $`
- NO `\text{...}` inside `\intertext{}`

### 2. Variable Repetition Rule (CRITICAL)
```latex
% GOOD:
t &= \frac{1}{\sqrt{g}} \int_{0}^{l} x^{-1/2} \, dx \\
  &= \frac{1}{\sqrt{g}} \left[ 2\sqrt{x} \right]_{0}^{l} \\
  &= 2\sqrt{\frac{l}{g}} \\
  &= 1.0 \ \mathrm{s}

% BAD (repetitive):
t &= \frac{1}{\sqrt{g}} \int_{0}^{l} x^{-1/2} \, dx \\
t &= \frac{1}{\sqrt{g}} \left[ 2\sqrt{x} \right]_{0}^{l} \\
t &= 2\sqrt{\frac{l}{g}} \\
t &= 1.0 \ \mathrm{s}
```

Rule: First line has variable, intermediate lines use `&=` only.

### 3. Diagram Placement
```latex
\begin{solution}
\begin{align*}
\intertext{Initial reasoning}
\sum F &= ma \\
T - mg &= ma
\end{align*}

\begin{center}
\begin{tikzpicture}
% TikZ diagram code
\end{tikzpicture}
\end{center}

\begin{align*}
\intertext{Continue from diagram}
a &= \frac{T - mg}{m} \\
  &= 0.2 \ \mathrm{m/s^2}
\end{align*}
\end{solution}
```

- Diagrams in `\begin{center}...\end{center}`
- Use `\begin{tikzpicture}...\end{tikzpicture}` for TikZ
- Diagrams interrupt flow, requiring separate `align*` blocks

### 4. Other Rules
- NO `\boxed{}` for final answers - just plain result
- NO blank lines inside `align*`
- One step per line
- Units: `\ \mathrm{m/s}` format
- Vectors: `\vec{v}`, unit vectors: `\hat{i}`
- Fractions: `\frac{a}{b}` - NEVER `\tfrac`
- Parentheses: `\left( ... \right)` - NO `\bigl`, `\bigr`

### 5. MCQ Solutions
```latex
\begin{solution}
\begin{align*}
\intertext{Brief analysis}
E &= \frac{kQ}{r^2} \\
  &= 1.8 \times 10^6 \ \mathrm{N/C}
\end{align*}

Therefore, the correct option is (c).
\end{solution}
```

Conclude with: "Therefore, the correct option is (X)."

## Updated Files

1. `vbagent/prompts/content_generation/solution/physics/common.py`
   - Updated `LATEX_FORMATTING_RULES` to match format_checker
   - Added templates: `SOLUTION_SIMPLE_TEMPLATE`, `SOLUTION_MCQ_TEMPLATE`

2. `vbagent/prompts/content_generation/solution/physics/mcq_sc.py`
   - Complete rewrite with exact formatting rules
   - Examples showing correct patterns
   - Diagram usage guidelines

3. `vbagent/prompts/content_generation/solution/physics/subjective.py`
   - Complete rewrite with exact formatting rules
   - Multi-part question handling
   - Comprehensive examples

## Examples

### Simple MCQ Solution
```latex
\begin{solution}
\begin{align*}
\intertext{Apply Newton's second law}
F &= ma \\
a &= \frac{F}{m} \\
  &= \frac{10}{2} \\
  &= 5 \ \mathrm{m/s^2}
\end{align*}

Therefore, the correct option is (b).
\end{solution}
```

### Solution with Diagram
```latex
\begin{solution}
\begin{align*}
\intertext{Analyze forces on the block}
\sum F &= ma \\
T - mg &= ma
\end{align*}

\begin{center}
\begin{tikzpicture}
\coordinate (O) at (0,0);
\draw[thick, ->] (O) -- (0,2) node[above] {$T$};
\draw[thick, ->] (O) -- (0,-1.5) node[below] {$mg$};
\fill (O) circle (2pt);
\end{tikzpicture}
\end{center}

\begin{align*}
\intertext{From the free body diagram}
a &= \frac{T - mg}{m} \\
  &= \frac{10 - 2 \times 9.8}{2} \\
  &= 0.2 \ \mathrm{m/s^2}
\end{align*}
\end{solution}
```

### Multi-part Subjective
```latex
\begin{solution}
\begin{align*}
\intertext{(a) Find the time period}
T &= 2\pi \sqrt{\frac{m}{k}} \\
  &= 2\pi \sqrt{\frac{0.5}{50}} \\
  &= 0.628 \ \mathrm{s}
\end{align*}

\begin{align*}
\intertext{(b) Find the maximum velocity}
v_{\text{max}} &= A\omega \\
               &= A \times \frac{2\pi}{T} \\
               &= 0.1 \times \frac{2\pi}{0.628} \\
               &= 1.0 \ \mathrm{m/s}
\end{align*}
\end{solution}
```

## Benefits

1. **Consistency**: Solutions match your existing format_checker standards
2. **Quality**: Clean, professional LaTeX output
3. **Maintainability**: Same formatting rules across scanner and solution stages
4. **Compatibility**: Works seamlessly with your existing compilation pipeline

## Next Steps

1. Test solution generation with real problems
2. Verify formatting matches format_checker expectations
3. Complete remaining question types (mcq_mc, assertion_reason, etc.)
4. Add chemistry and mathematics prompts following same pattern
