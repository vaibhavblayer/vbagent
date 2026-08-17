"""Standalone subject classifier for image and LaTeX inputs."""

from typing import TYPE_CHECKING

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.models.classification import Subject
from vbagent.prompts.subjects import SUBJECTS

if TYPE_CHECKING:
    from agents import Agent


def get_subject_classifier_prompt() -> str:
    """Prompt to have the agent infer the subject."""
    subjects_list = ", ".join(SUBJECTS)
    return f"""You are an expert educator who can distinguish between physics, chemistry, mathematics, and biology problems.
Analyze the provided question image and answer with only the subject name: {subjects_list}.
Respond with one of: {subjects_list}. Include no additional text or formatting."""


def create_subject_classifier() -> "Agent":
    """Create the standalone subject classifier."""
    prompt = get_subject_classifier_prompt()
    return create_agent(
        name="SubjectClassifier",
        instructions=prompt,
        output_type=str,
        agent_type="classifier",
    )


def classify_image_subject(image_path: str) -> Subject:
    """Classify the subject of an image."""
    agent = create_subject_classifier()
    response = run_agent_sync(agent, create_image_message(image_path, "Determine the subject."), timeout=20)
    candidate = str(response).strip().lower()
    if candidate not in SUBJECTS:
        raise ValueError(f"Detected '{candidate}' is not a valid subject: {SUBJECTS}")
    return candidate  # type: ignore[return-value]


def classify_latex_subject(latex_content: str) -> Subject:
    """Classify the subject of LaTeX content."""
    agent = create_subject_classifier()
    context = (
        "Determine the subject of the following question based on this LaTeX content. "
        "Respond with only one subject name."
    )
    payload = f"""{context}

```
{latex_content}
```
"""
    response = run_agent_sync(agent, payload, timeout=15)
    candidate = str(response).strip().lower()
    if candidate not in SUBJECTS:
        raise ValueError(f"Detected '{candidate}' is not a valid subject: {SUBJECTS}")
    return candidate  # type: ignore[return-value]


__all__ = [
    "get_subject_classifier_prompt",
    "create_subject_classifier",
    "classify_image_subject",
    "classify_latex_subject",
]
