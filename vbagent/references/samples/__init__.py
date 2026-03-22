"""Golden sample files for formatting reference.

Each .tex file is a complete, perfectly formatted example for a specific
subject × question_type combination. Used by the ProblemOrchestrator to
give every agent a consistent formatting reference.

Structure:
    samples/
    ├── physics/
    │   ├── mcq_sc.tex
    │   ├── mcq_mc.tex
    │   ├── subjective.tex
    │   └── assertion_reason.tex
    ├── chemistry/
    │   ├── mcq_sc.tex
    │   ├── mcq_mc.tex
    │   └── subjective.tex
    └── mathematics/
        ├── mcq_sc.tex
        ├── mcq_mc.tex
        └── subjective.tex
"""

from pathlib import Path
from typing import Optional

SAMPLES_DIR = Path(__file__).parent


def get_sample(subject: str, question_type: str) -> Optional[str]:
    """Load a golden sample for the given subject and question type.

    Args:
        subject: physics, chemistry, or mathematics
        question_type: mcq_sc, mcq_mc, subjective, assertion_reason, etc.

    Returns:
        The sample .tex content, or None if no sample exists.
    """
    sample_path = SAMPLES_DIR / subject / f"{question_type}.tex"
    if sample_path.exists():
        return sample_path.read_text()

    # Fallback: try mcq_sc as default
    fallback = SAMPLES_DIR / subject / "mcq_sc.tex"
    if fallback.exists():
        return fallback.read_text()

    return None


def list_samples() -> dict[str, list[str]]:
    """List all available samples grouped by subject."""
    result = {}
    for subject_dir in SAMPLES_DIR.iterdir():
        if subject_dir.is_dir() and not subject_dir.name.startswith("_"):
            types = [f.stem for f in subject_dir.glob("*.tex")]
            if types:
                result[subject_dir.name] = sorted(types)
    return result
