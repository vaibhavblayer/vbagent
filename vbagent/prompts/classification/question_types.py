"""Detailed heuristics for question-type detection."""

from typing import Literal

SubjectQuestionType = Literal[
    "mcq_sc",
    "mcq_mc",
    "subjective",
    "assertion_reason",
    "passage",
    "match",
]

QUESTION_TYPE_GUIDANCE = """Question type cues and evidence:
- mcq_sc: The question explicitly asks for one correct option, uses phrasing like "choose the correct option", "only one answer is correct", or presents a single blank followed by options labeled (A), (B), etc. The answers are typically called out as i), ii) or a), b), and there are no repeated statements that imply multiple correct answers.
- mcq_mc: Look for phrases such as "select all that apply", "two of the following", "more than one answer can be correct", or checkboxes/boxes that invite multiple ticks. In LaTeX you might see \CorrectChoice/\CorrectChoices macros, or instructions referencing "multiple answers" or "select the correct statements".
- subjective: Problems using words like "derive", "show that", "explain", "prove", or that demand step-by-step reasoning or calculations without predefined answer choices. The writer often uses phrases such as "calculate", "find the value", or open-ended prompts that require derivation or explanation.
- assertion_reason: Look for two statements labeled (A) and (R), followed by instructions such as "Assertion and Reason", "If both Assertion and Reason are true", or "Identify the correct relationship between A and R". LaTeX may use dedicated environments or text blocks with Assertion/Reason labels.
- passage: There is a shared passage/graph/diagram at the top with multiple numbered questions (e.g., 42, 43, 44) referring back to the same context. Keywords include "passage", "comprehension", "read the following", or question ranges like [42-45], and questions often reference "the above passage".
- match: The layout shows two columns with headers like "List I" and "List II", followed by "Match the following" instructions. Items are paired (A ↔ 1), and the question explicitly asks to match statements/columns rather than select a single option.

Always pick the type that matches the instructions and structure of the question, even if several cues appear; passage-type questions take precedence when many numbered items share the same context."""


def get_question_type_guidance() -> str:
    """Return the shared guidance string."""
    return QUESTION_TYPE_GUIDANCE
