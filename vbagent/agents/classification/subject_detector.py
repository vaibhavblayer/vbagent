"""Subject detection agent for multi-subject classification."""

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.models.classification import Subject
from vbagent.prompts.subjects import SUBJECTS


def get_subject_detector_prompt() -> str:
    """Prompt to have the agent infer the subject."""
    subjects_list = ", ".join(SUBJECTS)
    return f"""You are an expert educator who can distinguish between physics, chemistry, mathematics, and biology problems.
Analyze the provided question image and answer with only the subject name: {subjects_list}.
Respond with one of: {subjects_list}. Include no additional text or formatting."""


def create_subject_detector_agent() -> "Agent":
    from vbagent.agents.base import create_agent

    prompt = get_subject_detector_prompt()
    return create_agent(
        name="SubjectDetector",
        instructions=prompt,
        output_type=str,
        agent_type="classifier",
    )


def detect_subject_from_image(image_path: str) -> Subject:
    """Run subject detector on an image."""
    agent = create_subject_detector_agent()
    response = run_agent_sync(agent, create_image_message(image_path, "Determine the subject."), timeout=20)
    candidate = str(response).strip().lower()
    if candidate not in SUBJECTS:
        raise ValueError(f"Detected '{candidate}' is not a valid subject: {SUBJECTS}")
    return candidate  # type: ignore[return-value]


def detect_subject_from_latex(latex_content: str) -> Subject:
    """Run subject detector on LaTeX content."""
    agent = create_subject_detector_agent()
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
