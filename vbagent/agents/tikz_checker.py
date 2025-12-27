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
from vbagent.prompts.tikz_checker import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    PATCH_SYSTEM_PROMPT,
    PATCH_USER_TEMPLATE,
)


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
    prompt = SYSTEM_PROMPT
    
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
    
    prompt = PATCH_SYSTEM_PROMPT
    
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


def clean_latex_output(latex: str) -> str:
    """Clean up LaTeX output by removing markdown code block markers.
    
    Args:
        latex: Raw LaTeX output from LLM
        
    Returns:
        Cleaned LaTeX without markdown artifacts
    """
    if not latex:
        return latex
    
    # Remove markdown code block markers
    latex = re.sub(r'^```(?:latex|tex|LaTeX)?\s*\n?', '', latex, flags=re.IGNORECASE)
    latex = re.sub(r'\n?```\s*$', '', latex)
    latex = re.sub(r'^```\s*', '', latex)
    
    return latex.strip()



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
    from vbagent.agents.base import create_image_message, _print_agent_info
    
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
    
    _print_agent_info(agent)
    
    # Run the agent
    result = Runner.run_sync(agent, input=message)
    
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
    
    Args:
        result: Raw result from checker
        check_type: Type of check (TIKZ_CHECK)
        
    Returns:
        Tuple of (passed, summary, corrected_content)
    """
    # Check if passed
    passed_pattern = rf'%\s*{check_type}:\s*PASSED'
    if re.search(passed_pattern, result, re.IGNORECASE):
        match = re.search(rf'%\s*{check_type}:\s*PASSED\s*[-–—]?\s*(.*?)(?:\n|$)', result, re.IGNORECASE)
        summary = match.group(1).strip() if match else "No TikZ errors found"
        return True, summary, ""
    
    # Extract summary from comment
    summary_pattern = rf'%\s*{check_type}:\s*(.*?)(?:\n|$)'
    summary_match = re.search(summary_pattern, result, re.IGNORECASE)
    summary = summary_match.group(1).strip() if summary_match else "TikZ issues found and corrected"
    
    # Remove the check comment line to get clean content
    corrected_content = re.sub(rf'%\s*{check_type}:.*?\n', '', result, count=1, flags=re.IGNORECASE)
    corrected_content = corrected_content.strip()
    
    return False, summary, corrected_content


def has_tikz_passed(result: str) -> bool:
    """Check if TikZ check passed."""
    return '% TIKZ_CHECK: PASSED' in result or 'TIKZ_CHECK: PASSED' in result.upper()


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
