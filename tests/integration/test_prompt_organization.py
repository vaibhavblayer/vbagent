"""Property tests for prompt file organization.

**Feature: physics-question-pipeline, Property 15: Prompt File Organization**
**Validates: Requirements 11.3**
"""

import importlib
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


# List of all agent types that should have prompt files
AGENT_PROMPT_MODULES = [
    "vbagent.prompts.classifier",
]


def get_all_prompt_modules() -> list[str]:
    """Get all prompt module paths that exist in the prompts directory."""
    prompts_dir = Path("vbagent/prompts")
    modules = []
    
    for py_file in prompts_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        module_name = f"vbagent.prompts.{py_file.stem}"
        modules.append(module_name)
    
    # Also check subdirectories
    for subdir in prompts_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("_"):
            for py_file in subdir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                module_name = f"vbagent.prompts.{subdir.name}.{py_file.stem}"
                modules.append(module_name)
    
    return modules


@pytest.mark.parametrize("module_path", AGENT_PROMPT_MODULES)
def test_prompt_module_has_required_constants(module_path: str):
    """
    **Feature: physics-question-pipeline, Property 15: Prompt File Organization**
    **Validates: Requirements 11.3**
    
    For any agent, there SHALL exist a corresponding prompt file containing
    both SYSTEM_PROMPT and USER_TEMPLATE constants.
    """
    module = importlib.import_module(module_path)
    
    # Check SYSTEM_PROMPT exists and is a non-empty string
    assert hasattr(module, "SYSTEM_PROMPT"), (
        f"Module {module_path} missing SYSTEM_PROMPT constant"
    )
    assert isinstance(module.SYSTEM_PROMPT, str), (
        f"SYSTEM_PROMPT in {module_path} must be a string"
    )
    assert len(module.SYSTEM_PROMPT.strip()) > 0, (
        f"SYSTEM_PROMPT in {module_path} must not be empty"
    )
    
    # Check USER_TEMPLATE exists and is a non-empty string
    assert hasattr(module, "USER_TEMPLATE"), (
        f"Module {module_path} missing USER_TEMPLATE constant"
    )
    assert isinstance(module.USER_TEMPLATE, str), (
        f"USER_TEMPLATE in {module_path} must be a string"
    )
    assert len(module.USER_TEMPLATE.strip()) > 0, (
        f"USER_TEMPLATE in {module_path} must not be empty"
    )


# Property-based test using hypothesis
@given(st.sampled_from(AGENT_PROMPT_MODULES))
@settings(max_examples=len(AGENT_PROMPT_MODULES))
def test_property_prompt_file_organization(module_path: str):
    """
    **Feature: physics-question-pipeline, Property 15: Prompt File Organization**
    **Validates: Requirements 11.3**
    
    Property: For any agent, there SHALL exist a corresponding prompt file
    containing both SYSTEM_PROMPT and USER_TEMPLATE constants.
    """
    module = importlib.import_module(module_path)
    
    # Property 1: SYSTEM_PROMPT must exist and be a non-empty string
    assert hasattr(module, "SYSTEM_PROMPT")
    assert isinstance(module.SYSTEM_PROMPT, str)
    assert len(module.SYSTEM_PROMPT.strip()) > 0
    
    # Property 2: USER_TEMPLATE must exist and be a non-empty string
    assert hasattr(module, "USER_TEMPLATE")
    assert isinstance(module.USER_TEMPLATE, str)
    assert len(module.USER_TEMPLATE.strip()) > 0
