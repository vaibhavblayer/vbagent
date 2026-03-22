"""TikZ checker agent for LaTeX diagrams.

Checks TikZ/PGF code for syntax errors, best practices,
and physics diagram conventions.

Supports two modes:
1. Legacy mode: Returns full corrected content (check_tikz)
2. Patch mode: Uses apply_patch tool for structured diffs (check_tikz_with_patch)
"""

import re
from dataclasses import dataclass
from typing import Optional

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.diagram.tikz_checker import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    PATCH_USER_TEMPLATE,
)
from vbagent.utils.latex import clean_latex_output


@dataclass
class PatchResult:
    """Result from patch-based TikZ check."""
    passed: bool
    summary: str
    corrected_content: str  # Empty if passed
    patches_applied: int
    patch_errors: list[str]


def _get_tikz_reference_context(
    classification=None,
    diagram_type: Optional[str] = None,
) -> str:
    """Get TikZ reference context for the checker.
    
    Uses the same TikZReferenceStore as the generator for consistency.
    
    Args:
        classification: Optional ClassificationResult for metadata matching
        diagram_type: Optional filter by diagram type (e.g., 'circuit')
        
    Returns:
        Formatted context string with matching TikZ examples
    """
    try:
        from vbagent.references.tikz_store import TikZReferenceStore
        
        store = TikZReferenceStore.get_instance()
        
        if not store.enabled or not store.references:
            return ""
        
        # If classification provided, use metadata matching
        if classification:
            context = store.get_context_for_classification(classification)
        elif diagram_type:
            # Filter by diagram type
            refs = store.list_references(diagram_type=diagram_type)
            refs = refs[:store.max_examples]
            if not refs:
                return ""
            
            parts = []
            for ref in refs:
                header = f"% === Reference: {ref.name} ==="
                if ref.metadata.diagram_type:
                    header += f"\n% Type: {ref.metadata.diagram_type}"
                if ref.metadata.topic:
                    header += f", Topic: {ref.metadata.topic}"
                parts.append(f"{header}\n{ref.tikz_code}")
            context = "\n\n".join(parts)
        else:
            # Get general examples (top by any criteria)
            refs = store.references[:store.max_examples]
            if not refs:
                return ""
            
            parts = []
            for ref in refs:
                header = f"% === Reference: {ref.name} ==="
                if ref.metadata.diagram_type:
                    header += f"\n% Type: {ref.metadata.diagram_type}"
                parts.append(f"{header}\n{ref.tikz_code}")
            context = "\n\n".join(parts)
        
        if not context:
            return ""
        
        return f"""
## TikZ Reference Examples

Use these as style references for corrections:

{context}

---
"""
    except Exception:
        return ""


def create_tikz_checker_agent(
    use_context: bool = True,
    classification=None,
    diagram_type: Optional[str] = None,
):
    """Create a TikZ checker agent with optional reference context.
    
    Args:
        use_context: Whether to include reference context
        classification: Optional ClassificationResult for metadata matching
        diagram_type: Optional filter by diagram type (e.g., 'circuit')
        
    Returns:
        Configured Agent instance
    """
    from vbagent.prompts.diagram.tikz_checker import get_review_checklist
    
    # Build subject-aware checklist
    subject = getattr(classification, "subject", None) if classification else None
    checklist = get_review_checklist(subject)
    
    prompt = r"""You are an expert TikZ/PGF code reviewer. Check TikZ code for errors and provide ONLY the corrected version.

""" + checklist + r"""

## Output Format

**CRITICAL: Output ONLY what was given to you. Do NOT add document preamble, \documentclass, or any content that wasn't in the original.**

If issues found:
```
% TIKZ_CHECK: [Brief fixes description]
[EXACT corrected content - same structure as input]
```

If correct:
```
% TIKZ_CHECK: PASSED - No TikZ errors found
```

## Rules

1. Fix ONLY genuine errors
2. Preserve EXACT file structure - do NOT add preamble or packages not in original
3. Do NOT wrap in markdown code blocks
4. Keep the same content, just fix errors
"""
    
    if use_context:
        context = _get_tikz_reference_context(classification, diagram_type)
        if context:
            prompt = prompt + "\n" + context
    
    return create_agent(
        name="TikZChecker",
        instructions=prompt,
        agent_type="tikz_checker",
    )


class TikZPatchEditor:
    """Editor for collecting TikZ patches without immediately applying them.
    
    This editor collects patch operations so they can be reviewed
    before being applied to the file system.
    """
    
    def __init__(self, file_path: str, original_content: str):
        """Initialize the editor.
        
        Args:
            file_path: Path to the file being edited
            original_content: Original content of the file
        """
        self.file_path = file_path
        self.original_content = original_content
        self.current_content = original_content
        self.patches: list[dict] = []
        self.errors: list[str] = []
    
    def create_file(self, operation) -> dict:
        """Handle create_file operation (not expected for TikZ checker)."""
        self.errors.append(f"Unexpected create_file for {operation.path}")
        return {"status": "failed", "output": "create_file not supported"}
    
    def update_file(self, operation) -> dict:
        """Handle update_file operation by applying the diff."""
        from agents import apply_diff
        
        try:
            # Apply the V4A diff
            new_content = apply_diff(self.current_content, operation.diff)
            self.current_content = new_content
            self.patches.append({
                "type": "update_file",
                "path": operation.path,
                "diff": operation.diff,
            })
            return {"status": "completed", "output": f"Updated {operation.path}"}
        except Exception as e:
            error_msg = f"Failed to apply patch: {e}"
            self.errors.append(error_msg)
            return {"status": "failed", "output": error_msg}
    
    def delete_file(self, operation) -> dict:
        """Handle delete_file operation (not expected for TikZ checker)."""
        self.errors.append(f"Unexpected delete_file for {operation.path}")
        return {"status": "failed", "output": "delete_file not supported"}


def create_tikz_patch_agent(
    use_context: bool = True,
    classification=None,
    editor: Optional[TikZPatchEditor] = None,
    diagram_type: Optional[str] = None,
):
    """Create a TikZ checker agent with apply_patch tool.
    
    This agent uses the apply_patch tool to emit structured diffs
    instead of returning full corrected content.
    
    Args:
        use_context: Whether to include reference context
        classification: Optional ClassificationResult for metadata matching
        editor: Optional TikZPatchEditor instance (created if not provided)
        diagram_type: Optional filter by diagram type (e.g., 'circuit')
        
    Returns:
        Configured Agent instance with apply_patch tool
    """
    from agents import Agent, ApplyPatchTool
    from vbagent.config import get_model, get_model_settings
    from vbagent.prompts.diagram.tikz_checker import build_patch_system_prompt
    
    # Build subject-aware prompt
    subject = getattr(classification, "subject", None) if classification else None
    prompt = build_patch_system_prompt(subject)
    
    if use_context:
        context = _get_tikz_reference_context(classification, diagram_type)
        if context:
            prompt = prompt + "\n" + context
    
    # Create a dummy editor if none provided (will be replaced at runtime)
    if editor is None:
        editor = TikZPatchEditor("dummy.tex", "")
    
    return Agent(
        name="TikZPatchChecker",
        instructions=prompt,
        model=get_model("tikz_checker"),
        model_settings=get_model_settings("tikz_checker"),
        tools=[ApplyPatchTool(editor=editor)],
    )


# Legacy agent (created lazily for backward compatibility)
_tikz_checker_agent = None


def _get_tikz_checker_agent():
    """Get or create the legacy TikZ checker agent."""
    global _tikz_checker_agent
    if _tikz_checker_agent is None:
        _tikz_checker_agent = create_tikz_checker_agent(use_context=False)
    return _tikz_checker_agent


def check_tikz(
    full_content: str,
    image_path: str | None = None,
    use_context: bool = True,
    classification=None,
) -> tuple[bool, str, str]:
    """Check TikZ code for errors and best practices (legacy mode).
    
    Returns full corrected content. For structured diffs, use check_tikz_with_patch().
    
    Args:
        full_content: Full LaTeX file content containing TikZ code
        image_path: Optional path to reference image for comparison
        use_context: Whether to include reference context
        classification: Optional ClassificationResult for metadata matching
        
    Returns:
        Tuple of (passed, summary, corrected_content)
        
    Raises:
        ValueError: If content is empty
    """
    from vbagent.agents.base import create_image_message
    
    if not full_content.strip():
        raise ValueError("Content cannot be empty")
    
    # Create agent with context
    agent = create_tikz_checker_agent(use_context, classification)
    
    # Use string replace instead of .format() to avoid issues with LaTeX curly braces
    message_text = USER_TEMPLATE.replace('{full_content}', full_content)
    
    # If image provided, create multimodal message
    if image_path:
        message_text += "\n\n[Reference image provided - compare TikZ output against this image for accuracy]"
        message = create_image_message(image_path, message_text)
    else:
        message = message_text
    
    raw_result = run_agent_sync(agent, message)
    result = clean_latex_output(raw_result)
    
    return parse_check_result(result, "TIKZ_CHECK")


def check_tikz_with_patch(
    file_path: str,
    full_content: str,
    image_path: str | None = None,
    use_context: bool = True,
    classification=None,
    ref_diagram_type: Optional[str] = None,
) -> PatchResult:
    """Check TikZ code using apply_patch tool for structured diffs.
    
    Uses OpenAI's apply_patch tool to emit V4A diffs that can be
    reviewed and applied incrementally.
    
    Args:
        file_path: Path to the file being checked (for patch operations)
        full_content: Full LaTeX file content containing TikZ code
        image_path: Optional path to reference image for comparison
        use_context: Whether to include reference context
        classification: Optional ClassificationResult for metadata matching
        ref_diagram_type: Filter reference examples by diagram type (e.g., 'circuit')
        
    Returns:
        PatchResult with pass/fail status, summary, and corrected content
        
    Raises:
        ValueError: If content is empty
    """
    from agents import Runner
    from vbagent.agents.base import create_image_message
    from ..ui.logging import log_agent_usage
    import time
    
    if not full_content.strip():
        raise ValueError("Content cannot be empty")
    
    # Create editor to collect patches
    editor = TikZPatchEditor(file_path, full_content)
    
    # Create patch agent with the editor
    agent = create_tikz_patch_agent(use_context, classification, editor, ref_diagram_type)
    
    # Build the input message
    message_text = PATCH_USER_TEMPLATE.replace('{file_path}', file_path)
    message_text = message_text.replace('{full_content}', full_content)
    
    if image_path:
        message_text += "\n\n[Reference image provided - compare TikZ output against this image for accuracy]"
        message = create_image_message(image_path, message_text)
    else:
        message = message_text
    
    _start = time.time()
    
    # Run the agent
    result = Runner.run_sync(agent, input=message)
    
    _duration = time.time() - _start
    _usage = result.context_wrapper.usage if result.context_wrapper else None
    _resp_id = None
    try:
        if result.raw_responses:
            _resp_id = getattr(result.raw_responses[-1], "response_id", None)
    except (AttributeError, IndexError):
        pass
    log_agent_usage(agent.name, model=agent.model or "default", duration=_duration,
                    usage=_usage, response_id=_resp_id,
                    has_image=bool(image_path), reasoning="none")
    
    # Check if agent returned text indicating pass
    final_output = result.final_output or ""
    if "PASSED" in final_output.upper() or "no errors" in final_output.lower():
        return PatchResult(
            passed=True,
            summary="No TikZ errors found",
            corrected_content="",
            patches_applied=0,
            patch_errors=[],
        )
    
    # Get results from editor
    patches_applied = len(editor.patches)
    patch_errors = editor.errors
    
    # Determine pass/fail
    if patches_applied == 0 and not patch_errors:
        return PatchResult(
            passed=True,
            summary="No TikZ errors found",
            corrected_content="",
            patches_applied=0,
            patch_errors=[],
        )
    
    # Build summary
    if patches_applied > 0:
        summary = f"Applied {patches_applied} patch(es)"
    else:
        summary = "TikZ issues found but patches failed"
    
    if patch_errors:
        summary += f" ({len(patch_errors)} error(s))"
    
    return PatchResult(
        passed=False,
        summary=summary,
        corrected_content=editor.current_content if patches_applied > 0 else "",
        patches_applied=patches_applied,
        patch_errors=patch_errors,
    )



def parse_check_result(result: str, check_type: str) -> tuple[bool, str, str]:
    """Parse the check result to extract pass/fail status and content.

    Delegates to the shared implementation in quality.base.
    """
    from vbagent.agents.quality.base import parse_check_result as _parse
    return _parse(result, check_type)


def has_tikz_passed(result: str) -> bool:
    """Check if TikZ check passed."""
    from vbagent.agents.quality.base import has_check_passed
    return has_check_passed(result, "TIKZ_CHECK")


def has_tikz_environment(content: str) -> bool:
    """Check if content contains TikZ code."""
    tikz_patterns = [
        r'\\begin\{tikzpicture\}',
        r'\\tikz\s*[{\[]',
        r'\\draw\s*[\[\(]',
        r'\\node\s*[\[\(]',
        r'\\fill\s*[\[\(]',
        r'\\path\s*[\[\(]',
        r'\\begin\{axis\}',
    ]
    for pattern in tikz_patterns:
        if re.search(pattern, content):
            return True
    return False


# Backward compatibility: expose tikz_checker_agent as module-level
class _TikzCheckerAgentProxy:
    """Proxy for lazy loading tikz_checker_agent."""
    _agent = None
    
    def __getattr__(self, name):
        if self._agent is None:
            self._agent = _get_tikz_checker_agent()
        return getattr(self._agent, name)


tikz_checker_agent = _TikzCheckerAgentProxy()


# ---------------------------------------------------------------------------
# Structured validation (formerly in classification/tikz_checker.py)
# ---------------------------------------------------------------------------

_STRUCTURED_CHECKER_PROMPT = """You are an expert TikZ validator and fixer. Analyze TikZ code for errors and provide fixes.

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


def create_structured_tikz_checker_agent():
    """Create a TikZ checker agent that returns structured TikZValidation."""
    from vbagent.models.diagram import TikZValidation

    return create_agent(
        name="TikZChecker",
        instructions=_STRUCTURED_CHECKER_PROMPT,
        output_type=TikZValidation,
        agent_type="tikz_checker",
    )


def validate_tikz(
    tikz_code: str,
    context: Optional[str] = None,
    auto_fix: bool = True,
    compile_test: bool = True,
):
    """Validate and fix TikZ code, returning structured TikZValidation.

    Args:
        tikz_code: TikZ code to validate
        context: Optional context (problem description, diagram type)
        auto_fix: Whether to automatically apply fixes
        compile_test: Whether to test compilation

    Returns:
        TikZValidation with errors, fixes, and corrected code
    """
    agent = create_structured_tikz_checker_agent()

    validation_context = f"""Validate this TikZ code and fix any errors.

**TikZ Code:**
```latex
{tikz_code}
```
"""
    if context:
        validation_context += f"\n\n**Context:**\n{context}\n"

    validation_context += (
        f"\n\n**Auto-fix:** {auto_fix}\n"
        f"**Compile test:** {compile_test}\n\n"
        "Analyze the code, identify errors, and provide fixes."
    )

    result = run_agent_sync(agent, validation_context)

    if compile_test and result.fixed_tikz_code:
        from vbagent.compile import compile_latex

        compile_result = compile_latex(
            result.fixed_tikz_code, subject="physics", verbose=False
        )
        if compile_result.success:
            result.compilation_status = "success"
            result.is_valid = True
        else:
            result.compilation_status = "failed"
            result.is_valid = False
            if compile_result.error:
                from vbagent.models.diagram import TikZError

                result.errors_found.append(
                    TikZError(
                        type="compilation",
                        line=0,
                        message=compile_result.error,
                        severity="error",
                    )
                )

    return result


def check_and_fix_tikz(
    tikz_code: str, max_retries: int = 2
) -> tuple[bool, str, object]:
    """Check and fix TikZ code with retries.

    Args:
        tikz_code: TikZ code to check
        max_retries: Maximum fix attempts

    Returns:
        Tuple of (success, final_code, validation_result)
    """
    current_code = tikz_code
    result = None

    for attempt in range(max_retries + 1):
        result = validate_tikz(current_code, compile_test=True)

        if result.is_valid:
            return True, current_code, result

        if result.fixed_tikz_code and attempt < max_retries:
            current_code = result.fixed_tikz_code
        else:
            return False, current_code, result

    return False, current_code, result
