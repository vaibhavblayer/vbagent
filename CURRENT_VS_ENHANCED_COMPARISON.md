# Current vs Enhanced Solution Pipeline

## Your Test Case: Organ Pipe Problem

### Current Implementation (What You Just Ran)

```
Stage 1: Scanner
├─> Input: Original image
├─> Output: Problem + Solution (complete)
└─> No diagram detection

Stage 2: Solution Agent (NEW)
├─> Input: Original image + Scanned problem
├─> Output: Solution (complete, no diagram requirements)
└─> Result: Duplicate solution, no extra value
```

**Output from your test:**
```latex
\begin{solution}
\begin{align*}
\intertext{Given two successive harmonics $f_a = 400 \ \mathrm{Hz}$ and $f_b = 560 \ \mathrm{Hz}$...}
f_1 &= f_b - f_a \\
    &= 560 - 400 \\
    &= 160 \ \mathrm{Hz} \\
\intertext{If the pipe were open, $f_a$ should equal $n f_1$ for some integer $n$.}
\frac{f_a}{f_1} &= \frac{400}{160} \\
                &= 2.5 \\
\intertext{Since $2.5$ is not an integer, the harmonics cannot be...}
... (rest of solution)
\end{align*}
\end{solution}
```

**Issues:**
- ❌ No diagram generated (even though graph would help)
- ❌ No diagram requirements identified
- ❌ No rich context for diagram agents
- ❌ Solution agent just duplicates scanner work

---

## Enhanced Implementation (What We Should Build)

### Architecture

```
Stage 1: Scanner (Problem Only)
├─> Input: Original image
├─> Output: Problem text only (no solution)
└─> Fast, cheap model (gpt-4o-mini)

Stage 2: Solution Agent (Solution + Diagram Requirements)
├─> Input: Original image + Problem text
├─> Output: Solution + Diagram requirements with rich context
└─> Better model (gpt-4o)

Stage 3: Diagram Generation (Specialized Agents)
├─> Input: Original image + Rich context from solution
├─> Routing: FBD/Circuit/Graph/Optics agents
└─> Output: High-quality TikZ with proper context

Stage 4: Assembly
└─> Combine: Problem + Solution + Diagrams
```

### Enhanced Output for Your Test Case

**Stage 1: Scanner Output**
```latex
\item An organ pipe has two successive harmonics with frequencies $400$ and $560~\text{Hz}$. 
The speed of sound in air is $344~\text{m/s}$.
\renewcommand{\labelenumi}{(\alph{enumi})}
\begin{enumerate}
\item Is this an open or a closed pipe?
\item What two harmonics are there?
\item What is the length of the pipe?
\end{enumerate}
```

**Stage 2: Solution Agent Output**
```latex
\begin{solution}
\begin{align*}
\intertext{Given two successive harmonics $f_a = 400 \ \mathrm{Hz}$ and $f_b = 560 \ \mathrm{Hz}$, 
speed of sound $v = 344 \ \mathrm{m/s}$.}
\intertext{(a) Determine if pipe is open or closed. For an open pipe, successive harmonics 
differ by the fundamental frequency $f_1$.}
f_1 &= f_b - f_a \\
    &= 560 - 400 \\
    &= 160 \ \mathrm{Hz} \\
\intertext{If the pipe were open, $f_a$ should equal $n f_1$ for some integer $n$.}
\frac{f_a}{f_1} &= \frac{400}{160} = 2.5
\end{align*}

% DIAGRAM_NEEDED: graph
% CONTEXT: Comparison of harmonic frequency patterns for open vs closed pipes. Open pipe has 
% harmonics at f, 2f, 3f, 4f, 5f... (all integer multiples). Closed pipe has harmonics at 
% f, 3f, 5f, 7f... (odd integer multiples only). The given frequencies 400Hz and 560Hz are 
% marked on the graph. For open pipe, these would be at positions 2.5f and 3.5f (not integers). 
% For closed pipe, these are at positions 2.5f and 3.5f which correspond to the 2nd and 3rd 
% harmonics (3f and 5f where f=160Hz), confirming closed pipe.
% VALUES: f1=160Hz, fa=400Hz, fb=560Hz, v=344m/s, open_harmonics=[160,320,480,640,800], 
% closed_harmonics=[160,480,800,1120]
% LABELS: Frequency (Hz), Harmonic number, Open pipe pattern, Closed pipe pattern, 
% Given frequencies (400Hz, 560Hz)

\begin{align*}
\intertext{Since $2.5$ is not an integer, the pipe cannot be open. For a closed pipe, 
harmonics are at odd multiples: $f, 3f, 5f, 7f...$}
\frac{f_a}{f_1} &= \frac{400}{160} = 2.5 = \frac{5}{2} \\
\frac{f_b}{f_1} &= \frac{560}{160} = 3.5 = \frac{7}{2}
\intertext{These correspond to the 2nd and 3rd harmonics of a closed pipe (3f and 5f).}
\intertext{Therefore, this is a \textbf{closed pipe}.}
\end{align*}

\begin{align*}
\intertext{(b) The two harmonics are the 2nd and 3rd harmonics of a closed pipe:}
f_2 &= 3f_1 = 3 \times 160 = 480 \ \mathrm{Hz} \quad \text{(but given as 400Hz)} \\
f_3 &= 5f_1 = 5 \times 160 = 800 \ \mathrm{Hz} \quad \text{(but given as 560Hz)}
\intertext{Wait, let me recalculate. If $f_a = 400$ is the $n$-th harmonic and $f_b = 560$ 
is the $(n+1)$-th harmonic of a closed pipe:}
f_n &= (2n-1)f_1 \\
f_{n+1} &= (2n+1)f_1 \\
f_{n+1} - f_n &= 2f_1 = 160 \\
f_1 &= 80 \ \mathrm{Hz}
\intertext{Then:}
\frac{400}{80} &= 5 \quad \text{(5th harmonic, which is } (2 \times 3 - 1)f_1 = 5f_1\text{)} \\
\frac{560}{80} &= 7 \quad \text{(7th harmonic, which is } (2 \times 4 - 1)f_1 = 7f_1\text{)}
\intertext{Therefore, the two harmonics are the \textbf{5th and 7th harmonics} (or 3rd and 4th 
modes of a closed pipe).}
\end{align*}

\begin{align*}
\intertext{(c) For a closed pipe, the fundamental frequency is:}
f_1 &= \frac{v}{4L} \\
L &= \frac{v}{4f_1} \\
  &= \frac{344}{4 \times 80} \\
  &= \frac{344}{320} \\
  &= 1.075 \ \mathrm{m}
\intertext{Therefore, the length of the pipe is \textbf{1.075 m} or \textbf{107.5 cm}.}
\end{align*}
\end{solution}
```

**Stage 3: Diagram Agent Output**

Graph agent receives:
- **Original image**: Visual reference
- **Problem text**: Context about organ pipe
- **Solution context**: Detailed explanation of open vs closed pipe harmonics
- **Values**: `f1=80Hz, fa=400Hz, fb=560Hz, open=[80,160,240,320,400,480,560], closed=[80,240,400,560,720]`
- **Labels**: Frequency, Harmonic number, Open pipe, Closed pipe, Given frequencies

Generates:
```latex
\begin{center}
\begin{tikzpicture}
\begin{axis}[
    width=10cm, height=6cm,
    xlabel={Harmonic number},
    ylabel={Frequency (Hz)},
    xmin=0, xmax=8,
    ymin=0, ymax=800,
    grid=major,
    legend pos=north west,
    title={Open vs Closed Pipe Harmonics}
]

% Open pipe harmonics (all integer multiples)
\addplot[blue, mark=o, thick] coordinates {
    (1,80) (2,160) (3,240) (4,320) (5,400) (6,480) (7,560) (8,640)
};
\addlegendentry{Open pipe}

% Closed pipe harmonics (odd multiples only)
\addplot[red, mark=square, thick] coordinates {
    (1,80) (3,240) (5,400) (7,560)
};
\addlegendentry{Closed pipe}

% Mark given frequencies
\addplot[green, mark=*, only marks, mark size=4pt] coordinates {
    (5,400) (7,560)
};
\addlegendentry{Given frequencies}

% Annotations
\node[above] at (axis cs:5,400) {$f_a = 400$ Hz};
\node[above] at (axis cs:7,560) {$f_b = 560$ Hz};

\end{axis}
\end{tikzpicture}
\end{center}
```

---

## Comparison Table

| Aspect | Current (Your Test) | Enhanced (Proposed) |
|--------|-------------------|-------------------|
| **Scanner output** | Problem + Solution | Problem only |
| **Solution agent input** | Image + Problem | Image + Problem |
| **Solution agent output** | Complete solution | Solution + Diagram requirements |
| **Diagram detection** | ❌ None | ✅ Automatic |
| **Diagram context** | ❌ None | ✅ Rich (physics, values, labels) |
| **Diagram generation** | ❌ Not triggered | ✅ Specialized agents |
| **Extra value** | ❌ Duplicate work | ✅ Better diagrams, better explanations |

---

## What Extra Info We Get

### 1. Diagram Requirements Detection
- **Current**: No detection, no diagrams generated
- **Enhanced**: Automatically identifies when diagram would help

### 2. Rich Context for Diagrams
- **Current**: N/A
- **Enhanced**: 
  - `physics_context`: "Open pipe has harmonics at f, 2f, 3f... Closed pipe at f, 3f, 5f..."
  - `values`: Specific numbers to plot
  - `labels`: What to label on diagram

### 3. Better Diagram Quality
- **Current**: N/A
- **Enhanced**: Specialized agents with full context generate better TikZ

### 4. Separation of Concerns
- **Current**: Scanner does everything (problem + solution + diagrams)
- **Enhanced**: 
  - Scanner: Problem extraction (fast, cheap)
  - Solution: Physics reasoning (better model)
  - Diagrams: Specialized TikZ generation

---

## How We Decide Diagram is Needed

### Current Implementation
```python
# In solution.py - extract_diagram_requirements()
# Looks for: % DIAGRAM_NEEDED: <type>
# But solution prompts don't output this format yet!
```

### What We Need to Add

Update solution prompts to include diagram decision logic:

```
## When to Include Diagrams

**Always use diagrams for:**
1. Forces problems → FBD
2. Circuit problems → Circuit diagram
3. Optics problems → Ray diagram
4. Relationships between variables → Graph
5. Vector resolution → Vector diagram

**Example decision:**
- Problem mentions "forces on block" → Output: % DIAGRAM_NEEDED: fbd
- Problem asks "plot graph" → Output: % DIAGRAM_NEEDED: graph
- Problem about "lens and mirror" → Output: % DIAGRAM_NEEDED: optics
- Problem is pure calculation → No diagram needed
```

---

## Next Steps

1. **Update solution prompts** to output diagram requirements
2. **Test with problems that need diagrams** (FBD, circuits, graphs)
3. **Verify parsing** works correctly
4. **Compare quality** with old scanner
5. **Refine based on results**

Would you like me to implement the enhanced version with diagram detection?
