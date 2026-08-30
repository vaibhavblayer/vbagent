"""Shared CLI contract for selecting numbered problems."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any, TypeVar

import click


OPEN_ENDED_ITEM = sys.maxsize
CommandFunction = TypeVar("CommandFunction", bound=Callable[..., Any])


def item_selection_options(function: CommandFunction) -> CommandFunction:
    """Add the standard ``--from``, ``--to``, and ``--item`` options."""
    function = click.option(
        "--item",
        type=click.IntRange(min=1),
        default=None,
        help="Single item (shorthand for --from N --to N)",
    )(function)
    function = click.option(
        "--to",
        "to_index",
        type=click.IntRange(min=1),
        default=None,
        help="End item (1-based, inclusive)",
    )(function)
    function = click.option(
        "--from",
        "from_index",
        type=click.IntRange(min=1),
        default=None,
        help="Start item (1-based, inclusive)",
    )(function)
    return function


def resolve_item_range(
    from_index: int | None,
    to_index: int | None,
    item: int | None,
) -> tuple[int, int] | None:
    """Validate standard selection arguments and return an inclusive range.

    An omitted upper bound is represented by :data:`OPEN_ENDED_ITEM`, allowing
    directory and document consumers to select every available later item.
    """
    if item is not None and (from_index is not None or to_index is not None):
        raise click.UsageError("Use --item or --from/--to, not both")

    for option, value in (
        ("--from", from_index),
        ("--to", to_index),
        ("--item", item),
    ):
        if value is not None and value < 1:
            raise click.BadParameter(
                "must be positive (1-based)",
                param_hint=option,
            )

    if item is not None:
        return item, item
    if from_index is None and to_index is None:
        return None

    start = from_index or 1
    end = to_index or OPEN_ENDED_ITEM
    if start > end:
        raise click.UsageError("--from must be <= --to")
    return start, end
