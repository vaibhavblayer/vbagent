"""Small, dependency-free authorization hints from the terminal user's words.

These are deliberately conservative: model-supplied ``confirmed`` is not an
authorization, and a compile instruction never grants a generation permission.
Unknown wording falls back to one visible, plain-language approval question.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

DEFAULT_CHAT_REASONING_EFFORT = "medium"

AuthoringIntentPolicy = Literal[
    "create_now",
    "start_existing",
    "resume",
    "rebuild",
    "confirmation_required",
    "unspecified",
]


def _normalized(message: str) -> str:
    return " ".join(message.casefold().replace("’", "'").strip().split())


def is_confirmation_message(message: str) -> bool:
    return _normalized(message).rstrip(".!?") in {
        "/confirm",
        "/approve",
        "confirm",
        "approve",
        "go ahead",
        "proceed",
        "start",
        "start generation",
        "start it",
        "yes",
        "yes please",
        "yes start",
        "yes, start",
        "yes go ahead",
        "yes, go ahead",
        "do it",
    }


def is_decline_message(message: str) -> bool:
    return _normalized(message).rstrip(".!?") in {
        "/decline",
        "decline",
        "no",
        "no thanks",
        "no, thanks",
        "not now",
        "not yet",
        "don't start",
        "do not start",
    }


@dataclass(frozen=True)
class ChatIntent:
    policy: AuthoringIntentPolicy = "unspecified"
    after_completion: bool = False
    selection_requested: bool = False
    problem_numbers: tuple[int, ...] | None = None
    run_ids: tuple[str, ...] = ()


def _selected_numbers(text: str) -> tuple[int, ...] | None:
    """Read explicit human file numbers, never topic counts or run ordinals."""
    filenames = re.findall(r"\bproblem_(\d+)(?:\.tex)?\b", text)
    if filenames:
        return tuple(dict.fromkeys(int(number) for number in filenames))
    # The terminal supports bounded explicit lists/ranges. More elaborate
    # selection remains the controller's job, with a nonempty tool selection.
    match = re.search(
        r"\b(?:problems?|questions?|numbers?|files?|include|use|keep|compile|recompile|assemble|rebuild|export)\b"
        r"[^\d]*?(\d+(?:\s*(?:,|and|&|to|through|-)\s*\d+)*)"
        r"(?=\s*(?:$|[.!?]|only\b|please\b|in\b|into\b|to\b|and compile\b))",
        text,
    )
    if match is None:
        return None
    numbers: list[int] = []
    for part in re.split(r"\s*(?:,|and|&)\s*", match.group(1)):
        range_match = re.fullmatch(r"(\d+)\s*(?:to|through|-)\s*(\d+)", part)
        if range_match:
            first, last = map(int, range_match.groups())
            if first < 1 or last < first or last - first >= 1000:
                return None
            numbers.extend(range(first, last + 1))
        elif part.isdecimal():
            numbers.append(int(part))
        else:
            return None
        if len(numbers) > 1000:
            return None
    return tuple(dict.fromkeys(numbers))


def classify_authoring_intent(message: str) -> ChatIntent:
    """Authorize direct instructions, not mentions, quotations or hypotheticals."""
    normalized = _normalized(message)
    run_ids = tuple(re.findall(r"\b[a-f0-9]{12,64}\b", normalized))
    base = {"run_ids": run_ids}
    if any(
        phrase in normalized
        for phrase in (
            "do not start",
            "don't start",
            "not yet",
            "ask me before",
            "ask before",
            "confirm with me",
            "wait for my confirmation",
            "wait for confirmation",
            "let me approve",
            "approval first",
            "confirm first",
            "before starting",
            "before you start",
            "without starting",
            "plan only",
            "preflight only",
            "preview only",
            "show me the plan",
            "show the plan",
            "after i approve",
            "after my confirmation",
            "once i approve",
            "if i approve",
            "only after",
            "when i say",
        )
    ) or re.search(
        r"\b(?:don't|do not|never)\s+(?:\w+\s+){0,2}"
        r"(?:create|generate|start|resume|compile|rebuild|include)\b",
        normalized,
    ):
        return ChatIntent(policy="confirmation_required", **base)

    body = re.sub(r"^(?:(?:hey|hi|okay|ok|also)[,!]?\s+)+", "", normalized)
    body = re.sub(r"^(?:can|could|would|will) you\s+", "", body)
    body = re.sub(r"^(?:i want you to|i'd like you to|please)\s+", "", body)
    body = re.sub(r"^please\s+", "", body)
    body = re.sub(r"^copile\b", "compile", body)
    body = re.sub(r"^onlt\b", "only", body)

    if re.match(
        r"^(?:(?:show|give|prepare|create|make)\s+(?:me\s+)?(?:a\s+)?)?"
        r"(?:plan|preflight|preview)\b",
        body,
    ):
        return ChatIntent(policy="confirmation_required", **base)
    if re.match(
        r"^(?:how|why|what|should|does|will|is it|can it|can this|if|when|"
        r"explain|describe|suppose|imagine|check|review|don't|do not)\b",
        body,
    ):
        return ChatIntent(**base)

    # Selection directives are compilation instructions, not a request to
    # create the mentioned problems again. Numbers are human problem_N files.
    selection = bool(
        re.match(r"^(?:(?:only|just)\s+)?(?:include|use|keep)\b", body)
        and re.search(
            r"\b(?:problems?|questions?|files?|main\.tex|pdf|problem_\d+)\b", body
        )
        and not re.search(r"\b(?:ideas?|solutions?|reasoning|model)\b", body)
    )
    rebuild = (
        selection
        or bool(
            re.match(
                r"^(?:(?:only|just)\s+)?(?:compile|recompile|assemble|rebuild|export)\b",
                body,
            )
        )
        or bool(
            re.match(
                r"^(?:make|create|generate|build)\s+(?:the\s+)?(?:main\.tex|main\.pdf|pdf)\b",
                body,
            )
        )
    )
    if rebuild:
        if re.search(r"\b(?:except|excluding|exclude)\b", body):
            return ChatIntent(policy="confirmation_required", **base)
        selection = (
            selection
            or bool(
                re.search(
                    r"\b(?:only|just|selected)\b.*\b(?:problems?|questions?|files?|problem_\d+|\d+)\b",
                    body,
                )
            )
        ) and not bool(
            re.search(r"\ball (?:the )?(?:problems?|questions?|files?)\b", body)
        )
        return ChatIntent(
            policy="rebuild",
            after_completion=bool(
                re.search(
                    r"\b(?:after|once|when)\b.*\b(?:completion|completed|complete|"
                    r"finished|finishes|done)\b",
                    body,
                )
            ),
            selection_requested=selection,
            problem_numbers=_selected_numbers(body) if selection else None,
            **base,
        )
    target = r"(?:this|that|it|these|them|the\s+(?:run|plan|generation)|generation|run|now|[a-f0-9]{12,64})\b"
    if re.match(rf"^(?:resume|continue)(?:\s+{target}|\s*[.!?]*$)", body):
        return ChatIntent(policy="resume", **base)
    if re.match(rf"^(?:start|run|proceed|go ahead)(?:\s+{target}|\s*[.!?]*$)", body):
        return ChatIntent(policy="start_existing", **base)
    if re.match(r"^generate\s+(?:these|them|it)\b", body):
        return ChatIntent(policy="start_existing", **base)
    if re.match(
        r"^(?:create|generate|author|make|produce|write|build|draft|add|complete)\b",
        body,
    ) and re.search(
        r"\b(?:problems?|questions?|mcqs?|items?|variants?|worksheet|paper|test|"
        r"solutions?|ideas?|components?|these|them|it)\b",
        body,
    ):
        return ChatIntent(policy="create_now", **base)
    return ChatIntent(**base)


def authoring_intent_policy(message: str) -> AuthoringIntentPolicy:
    return classify_authoring_intent(message).policy
