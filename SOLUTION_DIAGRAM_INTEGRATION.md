# Solution-Diagram Integration Design

## Problem Statement

The solution agent has much better context about what diagrams should represent:
- Which forces to show in an FBD
- What the diagram is trying to illustrate
- Physical meaning and relationships
- Specific values and labels needed

The diagram agent needs:
- Original image (for visual reference)
- Rich description from solution agent
- Subject and diagram type routing

## Proposed Flow

```
Stage 1: Scanner (GPT-4o-mini)
  ↓ problem text + original image

Stage 2: Solution Generator (GPT-4o)
  ↓ solution + diagram requirements with RICH context
  
Stage 3: Diagram Generator (Subject-specific agents)
  Input: 
    - Original image (visual reference)
    - Rich description from solution (what to represent)
    - Subject (for routing)
    - Diagram type (for routing)
  ↓ TikZ code
  
Stage 4: Assembly
  → Final LaTeX with diagrams inserted
```

## Enhanced DiagramRequirement

```python
class DiagramRequirement:
    """Diagram requirement with rich context from solution."""
    
    def __init__(
        self,
        diagram_id: str,
        diagram_type: str,
        description: str,
        location: str = "inline",
        # NEW: Rich context from solution
        physics_context: Optional[str] = None,
        values: Optional[Dict[str, str]] = None,
        labels: Optional[List[str]] = None,
    ):
        self.diagram_id = diagram_id
        self.diagram_type = diagram_type
        self.description = description  # What to represent
        self.location = location
        
        # Rich context from solution agent
        self.physics_context = physics_context  # e.g., "Forces on block: T=10N upward, mg=19.6N downward"
        self.values = values or {}  # e.g., {"T": "10 N", "mg": "19.6 N", "a": "0.2 m/s^2"}
        self.labels = labels or []  # e.g., ["T", "mg", "N", "f"]
```

## Solution Agent Output Format

The solution agent should output diagram requirements in a structured comment:

```latex
\begin{solution}
\begin{align*}
\intertext{Analyze forces on the block}
\sum F &= ma \\
T - mg &= ma
\end{align*}

% DIAGRAM_REQUIREMENT: {
%   "id": "fbd_1",
%   "type": "fbd",
%   "description": "Free body diagram showing forces on block",
%   "physics_context": "Block of mass 2 kg suspended by tension T=10N, weight mg=19.6N downward, net force upward",
%   "values": {"T": "10 N", "mg": "19.6 N", "m": "2 kg"},
%   "labels": ["T", "mg"]
% }

\begin{center}
\begin{tikzpicture}
% PLACEHOLDER: fbd_1
\end{tikzpicture}
\end{center}

\begin{align*}
\intertext{From the free body diagram}
a &= \frac{T - mg}{m} \\
  &= 0.2 \ \mathrm{m/s^2}
\end{align*}
\end{solution}
```

## Diagram Generation with Rich Context

```python
def generate_diagram_from_solution(
    requirement: DiagramRequirement,
    original_image_path: str,
    subject: str,
) -> str:
    """Generate diagram with rich context from solution.
    
    Args:
        requirement: DiagramRequirement with rich context
        original_image_path: Path to original problem image
        subject: Subject for routing
        
    Returns:
        TikZ code
    """
    # Build enhanced description
    enhanced_description = requirement.description
    
    if requirement.physics_context:
        enhanced_description += f"\n\nPhysics Context: {requirement.physics_context}"
    
    if requirement.values:
        values_str = ", ".join([f"{k}={v}" for k, v in requirement.values.items()])
        enhanced_description += f"\n\nValues: {values_str}"
    
    if requirement.labels:
        labels_str = ", ".join(requirement.labels)
        enhanced_description += f"\n\nLabels needed: {labels_str}"
    
    # Route to appropriate agent
    from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
    
    tikz_code, agent_used = generate_tikz_with_routing(
        image_path=original_image_path,  # Visual reference
        description=enhanced_description,  # Rich context from solution
        subject=subject,
        diagram_type=requirement.diagram_type,
    )
    
    return tikz_code
```

## Example: FBD with Rich Context

### Solution Agent Output
```latex
% DIAGRAM_REQUIREMENT: {
%   "id": "fbd_1",
%   "type": "fbd",
%   "description": "Free body diagram of block on incline",
%   "physics_context": "Block of mass 2 kg on 30° incline. Forces: weight mg=19.6N vertically down, normal N perpendicular to incline, friction f down the incline. Block accelerates down with a=4.9 m/s^2",
%   "values": {"m": "2 kg", "theta": "30°", "mg": "19.6 N", "a": "4.9 m/s^2"},
%   "labels": ["mg", "N", "f", "a"]
% }
```

### Enhanced Description to FBD Agent
```
Free body diagram of block on incline

Physics Context: Block of mass 2 kg on 30° incline. Forces: weight mg=19.6N vertically down, normal N perpendicular to incline, friction f down the incline. Block accelerates down with a=4.9 m/s^2

Values: m=2 kg, theta=30°, mg=19.6 N, a=4.9 m/s^2

Labels needed: mg, N, f, a
```

### FBD Agent Receives
- Original image (visual reference of the setup)
- Enhanced description (what forces, directions, values)
- Subject: physics
- Diagram type: fbd

## Example: Circuit with Rich Context

### Solution Agent Output
```latex
% DIAGRAM_REQUIREMENT: {
%   "id": "circuit_1",
%   "type": "circuit",
%   "description": "Circuit with resistors in series and parallel",
%   "physics_context": "Two resistors R1=10Ω and R2=20Ω in series, connected to 12V battery. Total resistance 30Ω, current 0.4A flows through circuit",
%   "values": {"R1": "10 Ω", "R2": "20 Ω", "V": "12 V", "I": "0.4 A", "R_total": "30 Ω"},
%   "labels": ["R1", "R2", "V", "I"]
% }
```

### Enhanced Description to Circuit Agent
```
Circuit with resistors in series and parallel

Physics Context: Two resistors R1=10Ω and R2=20Ω in series, connected to 12V battery. Total resistance 30Ω, current 0.4A flows through circuit

Values: R1=10 Ω, R2=20 Ω, V=12 V, I=0.4 A, R_total=30 Ω

Labels needed: R1, R2, V, I
```

## Implementation Steps

### 1. Update Solution Agent Prompt

Add to solution prompts:
```python
DIAGRAM_CONTEXT_GUIDELINES = """
## Diagram Context (CRITICAL)

When you need a diagram in the solution, provide RICH context:

Format:
% DIAGRAM_REQUIREMENT: {
%   "id": "diagram_id",
%   "type": "fbd|circuit|graph|optics|...",
%   "description": "Brief description",
%   "physics_context": "Detailed explanation of what to show",
%   "values": {"var1": "value1", "var2": "value2"},
%   "labels": ["label1", "label2"]
% }

Example for FBD:
% DIAGRAM_REQUIREMENT: {
%   "id": "fbd_1",
%   "type": "fbd",
%   "description": "Free body diagram of block",
%   "physics_context": "Block mass 2kg on table. Forces: weight 19.6N down, normal 19.6N up, applied force 10N right, friction 2N left",
%   "values": {"m": "2 kg", "mg": "19.6 N", "N": "19.6 N", "F": "10 N", "f": "2 N"},
%   "labels": ["mg", "N", "F", "f"]
% }

Then place placeholder:
\begin{center}
\begin{tikzpicture}
% PLACEHOLDER: fbd_1
\end{tikzpicture}
\end{center}
"""
```

### 2. Update DiagramRequirement Class

```python
@dataclass
class DiagramRequirement:
    """Diagram requirement with rich context from solution."""
    diagram_id: str
    diagram_type: str
    description: str
    location: str = "inline"
    
    # Rich context from solution
    physics_context: Optional[str] = None
    values: Optional[Dict[str, str]] = None
    labels: Optional[List[str]] = None
    
    @classmethod
    def from_comment(cls, comment_text: str) -> "DiagramRequirement":
        """Parse diagram requirement from LaTeX comment."""
        import json
        import re
        
        # Extract JSON from comment
        match = re.search(r'DIAGRAM_REQUIREMENT:\s*({.*?})', comment_text, re.DOTALL)
        if not match:
            raise ValueError("Invalid diagram requirement format")
        
        data = json.loads(match.group(1))
        
        return cls(
            diagram_id=data["id"],
            diagram_type=data["type"],
            description=data["description"],
            physics_context=data.get("physics_context"),
            values=data.get("values"),
            labels=data.get("labels"),
        )
```

### 3. Update extract_diagram_requirements

```python
def extract_diagram_requirements(latex: str) -> List[DiagramRequirement]:
    """Extract diagram requirements from LaTeX with rich context.
    
    Looks for:
    % DIAGRAM_REQUIREMENT: {...}
    
    Args:
        latex: LaTeX string with diagram requirement comments
        
    Returns:
        List of DiagramRequirement objects with rich context
    """
    import re
    
    # Pattern: % DIAGRAM_REQUIREMENT: {...}
    pattern = r'%\s*DIAGRAM_REQUIREMENT:\s*({[^}]+})'
    matches = re.findall(pattern, latex, re.DOTALL)
    
    requirements = []
    for match in matches:
        try:
            req = DiagramRequirement.from_comment(f"DIAGRAM_REQUIREMENT: {match}")
            requirements.append(req)
        except Exception as e:
            # Fallback to simple parsing
            continue
    
    return requirements
```

### 4. Update Diagram Generation

```python
def generate_diagram_with_context(
    requirement: DiagramRequirement,
    original_image_path: str,
    subject: str,
    show_spinner: bool = True,
) -> str:
    """Generate diagram with rich context from solution.
    
    Args:
        requirement: DiagramRequirement with rich context
        original_image_path: Path to original problem image
        subject: Subject for routing
        show_spinner: Whether to show spinner
        
    Returns:
        TikZ code
    """
    # Build enhanced description
    enhanced_description = requirement.description
    
    if requirement.physics_context:
        enhanced_description += f"\n\n**Physics Context:** {requirement.physics_context}"
    
    if requirement.values:
        values_str = ", ".join([f"{k}={v}" for k, v in requirement.values.items()])
        enhanced_description += f"\n\n**Values:** {values_str}"
    
    if requirement.labels:
        labels_str = ", ".join(requirement.labels)
        enhanced_description += f"\n\n**Labels needed:** {labels_str}"
    
    # Route to appropriate agent
    from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
    
    tikz_code, agent_used = generate_tikz_with_routing(
        image_path=original_image_path,
        description=enhanced_description,
        subject=subject,
        diagram_type=requirement.diagram_type,
        show_spinner=show_spinner,
    )
    
    return tikz_code
```

### 5. Complete Pipeline

```python
def generate_complete_solution(
    image_path: str,
    classification: ClassificationResult,
    subject: str,
) -> str:
    """Complete pipeline: scan → solution → diagrams → assembly.
    
    Args:
        image_path: Path to original problem image
        classification: Classification result
        subject: Subject name
        
    Returns:
        Complete LaTeX with problem, solution, and diagrams
    """
    # Stage 1: Scan problem
    from vbagent.agents.content_generation.scanner import scan
    scan_result = scan(image_path, classification, subject=subject)
    
    # Stage 2: Generate solution with diagram requirements
    from vbagent.agents.content_generation.solution import generate_solution
    solution_result = generate_solution(
        problem=scan_result.latex,
        question_type=classification.question_type,
        subject=subject,
    )
    
    # Stage 3: Generate diagrams with rich context
    final_solution = solution_result.solution_latex
    
    for req in solution_result.diagram_requirements:
        tikz_code = generate_diagram_with_context(
            requirement=req,
            original_image_path=image_path,  # Visual reference
            subject=subject,
        )
        
        # Replace placeholder
        placeholder = f"% PLACEHOLDER: {req.diagram_id}"
        final_solution = final_solution.replace(placeholder, tikz_code)
    
    # Stage 4: Assemble
    complete_latex = scan_result.latex + "\n\n" + final_solution
    
    return complete_latex
```

## Benefits

### 1. Better Diagram Quality
- Diagram agents get rich context about what to represent
- Know exact values and labels needed
- Understand physical meaning

### 2. Visual Reference
- Original image provides visual reference for layout
- Helps diagram agent understand spatial relationships
- Reduces ambiguity

### 3. Subject-Specific Routing
- Automatically routes to correct agent (FBD, circuit, etc.)
- Uses subject-specific conventions
- Leverages specialized prompts

### 4. Separation of Concerns
- Solution agent: physics reasoning
- Diagram agent: visual representation
- Each does what it's best at

## Example Complete Flow

```python
# Input: image of physics problem
image_path = "problem.png"
classification = classify(image_path)  # MCQ, physics, has_diagram

# Stage 1: Scanner extracts problem
scan_result = scan(image_path, classification)
# → problem: "\item A block of mass 2 kg..."

# Stage 2: Solution with rich diagram context
solution_result = generate_solution(
    problem=scan_result.latex,
    question_type="mcq_sc",
    subject="physics"
)
# → solution with: % DIAGRAM_REQUIREMENT: {...rich context...}

# Stage 3: Generate diagrams
for req in solution_result.diagram_requirements:
    tikz = generate_diagram_with_context(
        requirement=req,  # Rich context from solution
        original_image_path=image_path,  # Visual reference
        subject="physics",  # Routes to FBD agent
    )
    # FBD agent receives:
    # - Original image (sees the setup)
    # - "Forces: T=10N up, mg=19.6N down, block mass 2kg"
    # - Values: {"T": "10 N", "mg": "19.6 N"}
    # - Labels: ["T", "mg"]

# Stage 4: Assembly
final_latex = assemble(scan_result, solution_result, diagrams)
```

## Next Steps

1. Update solution prompts with DIAGRAM_CONTEXT_GUIDELINES
2. Implement DiagramRequirement.from_comment()
3. Update extract_diagram_requirements() to parse rich context
4. Implement generate_diagram_with_context()
5. Test with real problems
