"""Structural validation for multipart subjective solutions."""

from __future__ import annotations

import re
from collections import Counter


_LIST_TOKEN_RE = re.compile(
    r"\\begin\{enumerate\}(?:\[[^\]]*\])?"
    r"|\\end\{enumerate\}"
    r"|\\item\b"
)
_ENUMERATE_OPTION_RE = re.compile(
    r"\\begin\{enumerate\}(?:\[([^\]]*)\])?"
)


def _enumerate_option(begin_token: str) -> str:
    """Return a whitespace-insensitive local option signature."""
    match = _ENUMERATE_OPTION_RE.fullmatch(begin_token)
    if not match or not match.group(1):
        return ""
    return re.sub(r"\s+", "", match.group(1))


def multipart_enumerate_shapes(latex: str) -> tuple[tuple[str, int], ...]:
    """Return local option and direct-item count for multipart lists."""
    stack: list[tuple[str, int]] = []
    shapes: list[tuple[str, int]] = []

    for match in _LIST_TOKEN_RE.finditer(latex or ""):
        token = match.group(0)
        if token.startswith(r"\begin{enumerate}"):
            stack.append((_enumerate_option(token), 0))
        elif token == r"\end{enumerate}":
            if stack:
                option, count = stack.pop()
                if count >= 2:
                    shapes.append((option, count))
        elif stack:
            option, count = stack[-1]
            stack[-1] = (option, count + 1)

    return tuple(shapes)


def multipart_enumerate_counts(latex: str) -> tuple[int, ...]:
    """Return direct item counts for every multipart enumerate block.

    Items in a nested enumerate are counted only for that nested block, not
    for its parent. The order of the returned counts follows closing order,
    which is irrelevant to the multiset comparison used by the validator.
    """
    return tuple(count for _, count in multipart_enumerate_shapes(latex))


def has_multipart_subjective_problem(problem_latex: str) -> bool:
    """Return whether the problem contains an enumerate of question parts."""
    return bool(multipart_enumerate_counts(problem_latex))


def has_matching_multipart_structure(
    problem_latex: str,
    candidate_latex: str,
) -> bool:
    """Return whether candidate LaTeX mirrors all multipart problem lists."""
    required = Counter(multipart_enumerate_shapes(problem_latex))
    if not required:
        return True
    actual = Counter(multipart_enumerate_shapes(candidate_latex))
    return all(
        actual[shape] >= block_count
        for shape, block_count in required.items()
    )


__all__ = [
    "multipart_enumerate_counts",
    "multipart_enumerate_shapes",
    "has_multipart_subjective_problem",
    "has_matching_multipart_structure",
]
