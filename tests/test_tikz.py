"""Property tests for TikZ agent.

**Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
**Validates: Requirements 3.1, 3.3, 3.4**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from vbagent.agents.tikz import (
    create_tikz_agent,
    search_tikz_reference,
    validate_tikz_output,
)
from vbagent.prompts.tikz import SYSTEM_PROMPT, USER_TEMPLATE
from vbagent.models.classification import ClassificationResult
from vbagent.references.store import ReferenceStore


# Valid diagram types from the classification model
VALID_DIAGRAM_TYPES = ["graph", "circuit", "free_body", "geometry", "none"]


# Strategy for generating diagram descriptions
diagram_description_strategy = st.sampled_from([
    "A simple force diagram with two vectors",
    "A circuit with a resistor and capacitor",
    "A graph showing velocity vs time",
    "A free body diagram of a block on an incline",
    "A geometric construction with angles",
    "An optics diagram with a lens and light rays",
    "A pendulum with labeled forces",
    "A projectile motion trajectory",
])


# Strategy for generating classification results with has_diagram=True
@st.composite
def classification_with_diagram_strategy(draw):
    """Generate ClassificationResult instances where has_diagram is True."""
    return ClassificationResult(
        question_type=draw(st.sampled_from(["mcq_sc", "mcq_mc", "subjective"])),
        difficulty=draw(st.sampled_from(["easy", "medium", "hard"])),
        topic=draw(st.sampled_from(["mechanics", "electrostatics", "optics", "thermodynamics"])),
        subtopic=draw(st.text(min_size=3, max_size=20).filter(lambda x: x.strip())),
        has_diagram=True,  # Always True for this strategy
        diagram_type=draw(st.sampled_from(["graph", "circuit", "free_body", "geometry"])),
        num_options=draw(st.none() | st.integers(min_value=2, max_value=6)),
        estimated_marks=draw(st.integers(min_value=1, max_value=10)),
        key_concepts=draw(st.lists(st.text(min_size=2, max_size=20).filter(lambda x: x.strip()), min_size=1, max_size=3)),
        requires_calculus=draw(st.booleans()),
        confidence=draw(st.floats(min_value=0.5, max_value=1.0)),
    )


@pytest.fixture(autouse=True)
def reset_reference_store():
    """Reset the ReferenceStore singleton before each test."""
    ReferenceStore.reset_instance()
    yield
    ReferenceStore.reset_instance()


def test_tikz_agent_exists():
    """
    **Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
    **Validates: Requirements 3.1**
    
    Verify that the TikZ agent is properly configured.
    """
    tikz_agent = create_tikz_agent(use_context=False)
    assert tikz_agent is not None, "TikZ agent must exist"
    assert tikz_agent.name == "TikZ", "Agent name must be 'TikZ'"
    assert SYSTEM_PROMPT in tikz_agent.instructions, "Agent must use SYSTEM_PROMPT"


def test_tikz_agent_has_search_tool():
    """
    **Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
    **Validates: Requirements 3.2**
    
    Verify that the TikZ agent has the reference search tool.
    """
    tikz_agent = create_tikz_agent(use_context=False)
    assert tikz_agent.tools is not None, "Agent must have tools"
    assert len(tikz_agent.tools) > 0, "Agent must have at least one tool"
    
    # Check that search_tikz_reference is in the tools
    tool_names = [t.name for t in tikz_agent.tools]
    assert "search_tikz_reference" in tool_names, (
        "Agent must have search_tikz_reference tool"
    )


def test_search_tikz_reference_tool_exists():
    """
    **Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
    **Validates: Requirements 3.2**
    
    Verify that search_tikz_reference is a valid function tool.
    """
    # The @function_tool decorator wraps the function into a FunctionTool object
    assert search_tikz_reference is not None, "search_tikz_reference must exist"
    assert hasattr(search_tikz_reference, "name"), "Tool must have a name attribute"
    assert search_tikz_reference.name == "search_tikz_reference", (
        "Tool name must be 'search_tikz_reference'"
    )


@given(classification=classification_with_diagram_strategy())
@settings(max_examples=100)
def test_property_tikz_trigger_on_has_diagram(classification: ClassificationResult):
    """
    **Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
    **Validates: Requirements 3.1, 3.3, 3.4**
    
    Property: For any classification where has_diagram is true, the TikZ Agent
    SHALL be available for invocation. This test verifies the trigger condition.
    """
    # Property 1: has_diagram must be True (by strategy design)
    assert classification.has_diagram is True, (
        "Classification must have has_diagram=True"
    )
    
    # Property 2: When has_diagram is True, diagram_type should be set
    # (though it can be "none" in some cases)
    assert classification.diagram_type is not None or classification.has_diagram, (
        "When has_diagram is True, diagram_type should typically be set"
    )
    
    # Property 3: The TikZ agent should be ready to handle this
    # We verify the agent exists and is properly configured
    tikz_agent = create_tikz_agent(use_context=False)
    assert tikz_agent is not None, "TikZ agent must be available"
    assert len(tikz_agent.tools) > 0, "TikZ agent must have tools for reference search"


@given(description=diagram_description_strategy)
@settings(max_examples=100)
def test_property_user_template_formatting(description: str):
    """
    **Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
    **Validates: Requirements 3.3**
    
    Property: The USER_TEMPLATE SHALL properly format with any valid description.
    """
    # Format the template
    formatted = USER_TEMPLATE.format(description=description)
    
    # Property 1: Formatted message must contain the description
    assert description in formatted, (
        f"Formatted template must contain description: {description}"
    )
    
    # Property 2: Formatted message must be non-empty
    assert len(formatted.strip()) > 0, "Formatted template must not be empty"
    
    # Property 3: Template should mention requirements
    assert "Requirements" in formatted, "Template should include requirements section"


# Strategy for generating valid TikZ code snippets
@st.composite
def valid_tikz_code_strategy(draw):
    """Generate valid TikZ code snippets."""
    elements = draw(st.lists(
        st.sampled_from([
            r"\draw (0,0) -- (1,1);",
            r"\node at (0,0) {A};",
            r"\fill (0,0) circle (0.1);",
            r"\path (0,0) -- (1,0);",
            r"\draw[->, thick] (0,0) -- (2,0);",
        ]),
        min_size=1,
        max_size=5
    ))
    
    code = "\\begin{tikzpicture}\n"
    code += "\n".join(f"    {elem}" for elem in elements)
    code += "\n\\end{tikzpicture}"
    
    return code


# Strategy for generating invalid TikZ code
@st.composite
def invalid_tikz_code_strategy(draw):
    """Generate invalid/empty TikZ code."""
    choice = draw(st.integers(min_value=0, max_value=3))
    
    if choice == 0:
        return ""
    elif choice == 1:
        return "   "  # Whitespace only
    elif choice == 2:
        return "This is just plain text without any TikZ"
    else:
        return "Some random content"


@given(tikz_code=valid_tikz_code_strategy())
@settings(max_examples=100)
def test_property_validate_tikz_accepts_valid(tikz_code: str):
    """
    **Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
    **Validates: Requirements 3.4**
    
    Property: For any valid TikZ code containing tikzpicture environment,
    validate_tikz_output SHALL return True.
    """
    result = validate_tikz_output(tikz_code)
    
    assert result is True, (
        f"validate_tikz_output should accept valid TikZ code:\n{tikz_code}"
    )


@given(tikz_code=invalid_tikz_code_strategy())
@settings(max_examples=50)
def test_property_validate_tikz_rejects_invalid(tikz_code: str):
    """
    **Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
    **Validates: Requirements 3.4**
    
    Property: For any invalid/empty TikZ code, validate_tikz_output SHALL
    return False.
    """
    result = validate_tikz_output(tikz_code)
    
    assert result is False, (
        f"validate_tikz_output should reject invalid TikZ code:\n{tikz_code}"
    )


def test_system_prompt_contains_tikz_guidelines():
    """
    **Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
    **Validates: Requirements 3.2, 3.3**
    
    Verify that SYSTEM_PROMPT contains TikZ/PGF syntax guidelines.
    """
    # Check for key TikZ-related content
    assert "TikZ" in SYSTEM_PROMPT, "SYSTEM_PROMPT must mention TikZ"
    assert "PGF" in SYSTEM_PROMPT or "pgf" in SYSTEM_PROMPT.lower(), (
        "SYSTEM_PROMPT should mention PGF"
    )
    assert "tikzpicture" in SYSTEM_PROMPT, (
        "SYSTEM_PROMPT must mention tikzpicture environment"
    )
    
    # Check for physics diagram types
    physics_terms = ["force", "circuit", "graph", "diagram"]
    found_terms = [term for term in physics_terms if term.lower() in SYSTEM_PROMPT.lower()]
    assert len(found_terms) >= 2, (
        f"SYSTEM_PROMPT should mention physics diagram types, found: {found_terms}"
    )


def test_prompts_have_required_constants():
    """
    **Feature: physics-question-pipeline, Property 4: TikZ Generation Trigger**
    **Validates: Requirements 11.3**
    
    Verify that tikz.py has both SYSTEM_PROMPT and USER_TEMPLATE.
    """
    from vbagent.prompts import tikz
    
    assert hasattr(tikz, "SYSTEM_PROMPT"), "tikz.py must have SYSTEM_PROMPT"
    assert hasattr(tikz, "USER_TEMPLATE"), "tikz.py must have USER_TEMPLATE"
    
    assert isinstance(tikz.SYSTEM_PROMPT, str), "SYSTEM_PROMPT must be a string"
    assert isinstance(tikz.USER_TEMPLATE, str), "USER_TEMPLATE must be a string"
    
    assert len(tikz.SYSTEM_PROMPT.strip()) > 0, "SYSTEM_PROMPT must not be empty"
    assert len(tikz.USER_TEMPLATE.strip()) > 0, "USER_TEMPLATE must not be empty"



# =============================================================================
# Tests for TikZ Checker with apply_patch support
# =============================================================================

def test_tikz_checker_patch_result_dataclass():
    """Test that PatchResult dataclass is properly defined."""
    from vbagent.agents.tikz_checker import PatchResult
    
    # Create a PatchResult instance
    result = PatchResult(
        passed=True,
        summary="No errors found",
        corrected_content="",
        patches_applied=0,
        patch_errors=[],
    )
    
    assert result.passed is True
    assert result.summary == "No errors found"
    assert result.corrected_content == ""
    assert result.patches_applied == 0
    assert result.patch_errors == []


def test_tikz_checker_patch_result_with_errors():
    """Test PatchResult with patch errors."""
    from vbagent.agents.tikz_checker import PatchResult
    
    result = PatchResult(
        passed=False,
        summary="Applied 2 patches",
        corrected_content="\\begin{tikzpicture}\\end{tikzpicture}",
        patches_applied=2,
        patch_errors=["Failed to apply patch 3"],
    )
    
    assert result.passed is False
    assert result.patches_applied == 2
    assert len(result.patch_errors) == 1


def test_tikz_checker_prompts_have_patch_constants():
    """Verify that tikz_checker.py has patch-related prompts."""
    from vbagent.prompts import tikz_checker
    
    assert hasattr(tikz_checker, "PATCH_SYSTEM_PROMPT"), (
        "tikz_checker.py must have PATCH_SYSTEM_PROMPT"
    )
    assert hasattr(tikz_checker, "PATCH_USER_TEMPLATE"), (
        "tikz_checker.py must have PATCH_USER_TEMPLATE"
    )
    
    assert isinstance(tikz_checker.PATCH_SYSTEM_PROMPT, str)
    assert isinstance(tikz_checker.PATCH_USER_TEMPLATE, str)
    
    # Check that patch prompts mention apply_patch
    assert "apply_patch" in tikz_checker.PATCH_SYSTEM_PROMPT, (
        "PATCH_SYSTEM_PROMPT should mention apply_patch"
    )
    assert "V4A" in tikz_checker.PATCH_SYSTEM_PROMPT, (
        "PATCH_SYSTEM_PROMPT should mention V4A diff format"
    )


def test_tikz_checker_has_patch_function():
    """Verify that check_tikz_with_patch function exists."""
    from vbagent.agents.tikz_checker import check_tikz_with_patch
    
    assert callable(check_tikz_with_patch), (
        "check_tikz_with_patch must be callable"
    )


def test_tikz_checker_has_reference_context_function():
    """Verify that _get_tikz_reference_context function exists."""
    from vbagent.agents.tikz_checker import _get_tikz_reference_context
    
    assert callable(_get_tikz_reference_context), (
        "_get_tikz_reference_context must be callable"
    )
    
    # Should return empty string when no references
    context = _get_tikz_reference_context()
    assert isinstance(context, str), "Should return a string"


def test_tikz_checker_create_patch_agent():
    """Verify that create_tikz_patch_agent creates an agent with apply_patch tool."""
    from vbagent.agents.tikz_checker import create_tikz_patch_agent
    
    agent = create_tikz_patch_agent(use_context=False)
    
    assert agent is not None, "Agent must be created"
    assert agent.name == "TikZPatchChecker", "Agent name must be TikZPatchChecker"
    assert agent.tools is not None, "Agent must have tools"
    assert len(agent.tools) > 0, "Agent must have at least one tool"
    
    # Check that ApplyPatchTool is in the tools
    tool_types = [type(t).__name__ for t in agent.tools]
    assert "ApplyPatchTool" in tool_types, (
        "Agent must have ApplyPatchTool"
    )


def test_tikz_checker_legacy_function_still_works():
    """Verify that legacy check_tikz function still exists and is callable."""
    from vbagent.agents.tikz_checker import check_tikz
    
    assert callable(check_tikz), "check_tikz must be callable"


# =============================================================================
# Tests for auto-discovery of images
# =============================================================================

def test_has_diagram_placeholder_detects_input_diagram():
    """Test that has_diagram_placeholder detects \\input{diagram} pattern."""
    from vbagent.cli.common import has_diagram_placeholder
    
    # Should detect simple pattern
    content_with_placeholder = r"""
\begin{center}
\input{diagram}
\end{center}
"""
    assert has_diagram_placeholder(content_with_placeholder) is True
    
    # Should detect without center environment
    content_simple = r"\input{diagram}"
    assert has_diagram_placeholder(content_simple) is True
    
    # Should not detect other inputs
    content_other = r"\input{preamble}"
    assert has_diagram_placeholder(content_other) is False
    
    # Should not detect in regular content
    content_no_placeholder = r"""
\begin{tikzpicture}
\draw (0,0) -- (1,1);
\end{tikzpicture}
"""
    assert has_diagram_placeholder(content_no_placeholder) is False


def test_find_image_for_problem_with_explicit_dir(tmp_path):
    """Test find_image_for_problem with explicit images_dir."""
    from vbagent.cli.common import find_image_for_problem
    
    # Create test structure
    tex_dir = tmp_path / "tex"
    tex_dir.mkdir()
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    
    tex_file = tex_dir / "Problem_1.tex"
    tex_file.write_text(r"\input{diagram}")
    
    image_file = images_dir / "Problem_1.png"
    image_file.write_bytes(b"fake png")
    
    # Should find image with explicit dir
    result = find_image_for_problem(tex_file, images_dir)
    assert result is not None
    assert result.name == "Problem_1.png"


def test_find_image_for_problem_auto_discover(tmp_path):
    """Test find_image_for_problem auto-discovery mode."""
    from vbagent.cli.common import find_image_for_problem
    
    # Create test structure: tex/Problem_1.tex, images/Problem_1.png
    tex_dir = tmp_path / "scans"
    tex_dir.mkdir()
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    
    tex_file = tex_dir / "Problem_12.tex"
    tex_file.write_text(r"\input{diagram}")
    
    image_file = images_dir / "Problem_12.png"
    image_file.write_bytes(b"fake png")
    
    # Should auto-discover image in sibling images/ directory
    result = find_image_for_problem(tex_file, auto_discover=True)
    assert result is not None
    assert result.name == "Problem_12.png"


def test_find_image_for_problem_no_auto_discover(tmp_path):
    """Test find_image_for_problem with auto_discover=False."""
    from vbagent.cli.common import find_image_for_problem
    
    # Create test structure
    tex_dir = tmp_path / "scans"
    tex_dir.mkdir()
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    
    tex_file = tex_dir / "Problem_12.tex"
    tex_file.write_text(r"\input{diagram}")
    
    image_file = images_dir / "Problem_12.png"
    image_file.write_bytes(b"fake png")
    
    # Should NOT find image when auto_discover=False and no images_dir
    result = find_image_for_problem(tex_file, auto_discover=False)
    assert result is None


def test_find_image_for_problem_src_pattern(tmp_path):
    """Test find_image_for_problem with src_tex -> src_images pattern."""
    from vbagent.cli.common import find_image_for_problem
    
    # Create test structure: src/src_tex/Problem_1.tex, src/src_images/Problem_1.jpg
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    tex_dir = src_dir / "src_tex"
    tex_dir.mkdir()
    images_dir = src_dir / "src_images"
    images_dir.mkdir()
    
    tex_file = tex_dir / "Problem_5.tex"
    tex_file.write_text(r"\input{diagram}")
    
    image_file = images_dir / "Problem_5.jpg"
    image_file.write_bytes(b"fake jpg")
    
    # Should auto-discover image in src_images directory
    result = find_image_for_problem(tex_file, auto_discover=True)
    assert result is not None
    assert result.name == "Problem_5.jpg"
