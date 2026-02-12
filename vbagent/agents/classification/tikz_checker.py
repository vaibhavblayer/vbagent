"""Agent 7: TikZ Checker/Validator.

Validates and fixes TikZ code automatically.
Ensures compilation success and best practices.
"""

from typing import Optional, Tuple

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.models.classification_v2 import TikZValidation
from vbagent.compile import compile_latex


def get_tikz_checker_prompt() -> str:
    """Get TikZ checker prompt."""
    return """You are an expert TikZ validator and fixer. Analyze TikZ code for errors and provide fixes.

You MUST respond with ONLY a valid JSON object:

{
    "is_valid": true | false,
    "compilation_status": "success" | "fixed" | "failed",
    "fixed_tikz_code": "<corrected code if fixes applied, else null>",
    "errors_found": [
        {
            "type": "syntax" | "missing_library" | "undefined_command" | "dimension" | "style",
            "line": <line number>,
            "message": "<error description>",
            "severity": "error" | "warning"
        }
    ],
    "fixes_applied": [
        {
            "type": "<fix type>",
            "description": "<what was fixed>",
            "before": "<original code snippet>",
            "after": "<fixed code snippet>"
        }
    ],
    "validation_metadata": {
        "libraries_used": ["<lib1>", "<lib2>"],
        "packages_required": ["<pkg1>", "<pkg2>"],
        "complexity_score": <1-10>,
        "compilation_time_ms": <estimated time>
    },
    "suggestions": ["<suggestion1>", "<suggestion2>"]
}

Common TikZ errors to check:
1. **Syntax errors**: Missing semicolons, unmatched braces, invalid coordinates
2. **Missing libraries**: calc, arrows.meta, positioning, decorations, patterns
3. **Undefined commands**: Custom commands without definition
4. **Dimension errors**: Missing units (cm, pt), invalid dimensions
5. **Style errors**: Undefined styles, invalid style syntax

Common fixes:
1. Add missing semicolons at end of paths
2. Add required TikZ libraries to \\usetikzlibrary{}
3. Fix coordinate syntax: (x,y) not (x y)
4. Add units to dimensions: 2cm not 2
5. Fix arrow syntax: ->, -latex, -stealth
6. Escape special characters in node text

Best practices:
1. Use \\usetikzlibrary{} for all required libraries
2. Define custom styles in preamble
3. Use meaningful coordinate names
4. Add comments for complex constructions
5. Use consistent spacing and indentation

Validation process:
1. Parse TikZ code structure
2. Identify errors and warnings
3. Apply automatic fixes where possible
4. Provide suggestions for manual fixes
5. Estimate compilation success

Respond with ONLY the JSON object."""


def create_tikz_checker_agent():
    """Create TikZ checker agent."""
    prompt = get_tikz_checker_prompt()
    
    return create_agent(
        name="TikZChecker",
        instructions=prompt,
        output_type=TikZValidation,
        agent_type="tikz_checker",
    )


def validate_tikz(
    tikz_code: str,
    context: Optional[str] = None,
    auto_fix: bool = True,
    compile_test: bool = True
) -> TikZValidation:
    """Validate and fix TikZ code (Agent 7).
    
    Args:
        tikz_code: TikZ code to validate
        context: Optional context (problem description, diagram type)
        auto_fix: Whether to automatically apply fixes
        compile_test: Whether to test compilation
        
    Returns:
        TikZValidation with errors, fixes, and corrected code
    """
    agent = create_tikz_checker_agent()
    
    # Build validation context
    validation_context = f"""Validate this TikZ code and fix any errors.

**TikZ Code:**
```latex
{tikz_code}
```
"""
    
    if context:
        validation_context += f"""

**Context:**
{context}
"""
    
    validation_context += f"""

**Auto-fix:** {auto_fix}
**Compile test:** {compile_test}

Analyze the code, identify errors, and provide fixes."""
    
    # Run validation agent
    result = run_agent_sync(agent, validation_context)
    
    # If compile test requested and code was fixed, test it
    if compile_test and result.fixed_tikz_code:
        compile_result = compile_latex(
            result.fixed_tikz_code,
            subject="physics",
            verbose=False
        )
        
        if compile_result.success:
            result.compilation_status = "success"
            result.is_valid = True
        else:
            result.compilation_status = "failed"
            result.is_valid = False
            
            # Add compilation error to errors list
            if compile_result.error:
                from vbagent.models.classification_v2 import TikZError
                result.errors_found.append(
                    TikZError(
                        type="compilation",
                        line=0,
                        message=compile_result.error,
                        severity="error"
                    )
                )
    
    return result


def check_and_fix_tikz(tikz_code: str, max_retries: int = 2) -> Tuple[bool, str, TikZValidation]:
    """Check and fix TikZ code with retries.
    
    Args:
        tikz_code: TikZ code to check
        max_retries: Maximum fix attempts
        
    Returns:
        Tuple of (success, final_code, validation_result)
    """
    current_code = tikz_code
    
    for attempt in range(max_retries + 1):
        result = validate_tikz(current_code, compile_test=True)
        
        if result.is_valid:
            return True, current_code, result
        
        if result.fixed_tikz_code and attempt < max_retries:
            current_code = result.fixed_tikz_code
        else:
            return False, current_code, result
    
    return False, current_code, result
