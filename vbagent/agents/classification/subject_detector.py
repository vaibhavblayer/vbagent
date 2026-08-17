"""Compatibility aliases for the renamed subject classifier."""

from .subject_classifier import (
    classify_image_subject,
    classify_latex_subject,
    create_subject_classifier,
    get_subject_classifier_prompt,
)

get_subject_detector_prompt = get_subject_classifier_prompt
create_subject_detector_agent = create_subject_classifier
detect_subject_from_image = classify_image_subject
detect_subject_from_latex = classify_latex_subject

__all__ = [
    "get_subject_detector_prompt",
    "create_subject_detector_agent",
    "detect_subject_from_image",
    "detect_subject_from_latex",
]
