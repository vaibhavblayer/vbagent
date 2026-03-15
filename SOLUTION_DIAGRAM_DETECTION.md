# Solution Stage: Diagram Detection & Rich Context

## Current Status

The solution generation pipeline has the **infrastructure** for diagram detection but it's **not being used yet**.

### What Exists ✅
1. `DiagramRequirement` class with rich context fields:
   - `physics_context`: Detailed explanation
   - `values`: Variable values dict
   - `labels`: Required labels list
   
2. `extract_diagram_requirements()` function to parse requirements from LaTeX

3. `generate_diagram_with_context()` to generate diagrams with rich context

4. `generate_complete_solution()` pipeline that should:
   - Generate solution with diagram requirements
   - Extract requirements
   - Generate diagrams with context
   - Assemble final output

### What's Missing ❌

The **solution prompts don't instruct the agent to output diagram requirements**. Currently:

```python
# Current behavior (from your test):
Solution agent generates:
\begin{solution}
\begin{align*}
... math steps ...
\end{align*}
\end{solution}

# No diagram requirements identified
# No placeholders for diagrams
# No rich context for diagram generation
```

## What We Need

### Option A: Diagram Requirements Format (Recommended)

Update solution prompts to output diagram requirements in parseable format:

```latex
\begin{solution}
\begin{align*}
\intertext{Given two successive harmonics...}
f_1 &= f_b - f_a \\
    &= 160 \ \mathrm{Hz}
\end{align*}

% DIAGRAM_REQUIREMENT: {
%   "id": "harmonics_comparison",
%   "type": "graph",
%   "description": "Graph showing harmonic frequencies for open vs closed pipe",
%   "location": "inline",
%   "physics_context": "Open pipe has harmonics at f, 2f, 3f... Closed pipe has harmonics at f, 3f, 5f... The given frequencies 400Hz and 560Hz differ by 160Hz, which would be 2.5f for open pipe (not integer multiple) but 2f for closed pipe (valid).",
%   "values": {
%     "f1": "160 Hz",
%     "f_a": "400 Hz", 
%     "f_b": "560 Hz"
%   },
%   "labels": ["Open pipe harmonics", "Closed pipe harmonics", "Given frequencies"]
% }

\begin{align*}
\intertext{From the analysis above...}
... rest of solution ...
\end{align*}
\end{solution}
```

### Option B: Simple Placeholder Format (Simpler)

```latex
\begin{solution}
\begin{align*}
... math ...
\end{align*}

% DIAGRAM_NEEDED: graph
% CONTEXT: Show comparison of open vs closed pipe harmonics
% VALUES: f1=160Hz, fa=400Hz, fb=560Hz
% LABELS: Open pipe, Closed pipe, Given frequencies

\begin{align*}
... more math ...
\end{align*}
\end{solution}
```

### Option C: Inline TikZ with Context Comments (Current)

Keep generating TikZ inline but add context comments:

```latex
\begin{solution}
\begin{align*}
... math ...
\end{align*}

\begin{center}
% DIAGRAM_CONTEXT: Open vs closed pipe harmonics
% VALUES: f1=160Hz, fa=400Hz, fb=560Hz
\begin{tikzpicture}
... tikz code ...
\end{tikzpicture}
\end{center}

\begin{align*}
... more math ...
\end{align*}
\end{solution}
```

## Recommendation

For your use case (testing phase, refinement needed), I recommend **Option B (Simple Placeholder)**:

### Why?
1. **Separation of concerns**: Solution agent focuses on physics, diagram agents focus on TikZ
2. **Better quality**: Diagram agents are specialized and have better TikZ skills
3. **Rich context**: Solution agent provides physics explanation, values, labels
4. **Easier refinement**: Can improve diagram generation without touching solution prompts
5. **Testable**: Can test solution quality separately from diagram quality

### Implementation

Update `vbagent/prompts/content_generation/solution/physics/subjective.py`:

```python
## Diagram Requirements

When a diagram would help understanding, output a diagram requirement instead of generating TikZ directly:

```latex
% DIAGRAM_NEEDED: <type>
% CONTEXT: <physics explanation>
% VALUES: <key=value pairs>
% LABELS: <comma-separated labels>
```

**Diagram types:**
- `fbd` - Free body diagram (forces on object)
- `circuit` - Electrical circuit
- `graph` - Plot/graph (x vs y)
- `optics` - Ray diagram (lenses/mirrors)
- `vector` - Vector diagram
- `geometry` - Geometric diagram

**Example:**
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For a block on an incline at angle $\\theta = 30^\\circ$}
\\sum F_x &= ma \\\\
mg \\sin\\theta &= ma
\\end{align*}

% DIAGRAM_NEEDED: fbd
% CONTEXT: Block on incline with weight mg resolved into components. Normal force N perpendicular to surface, friction f along surface, acceleration a down the incline.
% VALUES: m=2kg, theta=30deg, g=9.8m/s^2
% LABELS: mg, N, f, a, theta

\\begin{align*}
\\intertext{Solving for acceleration}
a &= g \\sin\\theta \\\\
  &= 4.9 \\ \\mathrm{m/s^2}
\\end{align*}
\\end{solution}
```

**When to use diagrams:**
- Forces: Always use FBD
- Circuits: Always show circuit diagram
- Motion: Use if trajectory/path is important
- Graphs: Use when showing relationships between variables
- Optics: Always use ray diagrams
- Vectors: Use when resolving components

**When NOT to use diagrams:**
- Simple numerical calculations
- Algebraic derivations without physical setup
- Problems where diagram doesn't add understanding
```

## Testing Plan

1. **Update subjective prompt** with diagram requirement format
2. **Test with FBD problem** (forces, incline, etc.)
3. **Verify parsing** - check `extract_diagram_requirements()` works
4. **Test diagram generation** - check rich context is passed
5. **Compare quality** - old scanner vs new solution+diagram
6. **Refine prompts** based on results

## Expected Benefits

### For Your Test Case (Organ Pipe Problem)

**Current output:** Just math, no diagram

**With diagram detection:**
```latex
\begin{solution}
\begin{align*}
... math showing 160Hz difference ...
\end{align*}

% DIAGRAM_NEEDED: graph
% CONTEXT: Comparison of harmonic frequencies for open pipe (f, 2f, 3f, 4f...) vs closed pipe (f, 3f, 5f, 7f...). The given frequencies 400Hz and 560Hz are shown, demonstrating they fit the closed pipe pattern (2.5f and 3.5f where f=160Hz).
% VALUES: f=160Hz, f2=400Hz, f3=560Hz, open_harmonics=[160,320,480,640], closed_harmonics=[160,480,800]
% LABELS: Frequency (Hz), Harmonic number, Open pipe, Closed pipe, Given frequencies

\begin{align*}
... rest of solution ...
\end{align*}
\end{solution}
```

Then diagram agent generates appropriate graph with:
- X-axis: Harmonic number
- Y-axis: Frequency
- Two series: open vs closed
- Markers at 400Hz and 560Hz
- Clear labels and legend

## Next Steps

1. Should we implement Option B (simple placeholder format)?
2. Which question types to update first? (subjective, mcq_sc, etc.)
3. Test with which diagram types first? (fbd, circuit, graph, optics)
