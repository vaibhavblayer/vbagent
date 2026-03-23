"""Idea collection pipeline — extracts ideas from various sources into the IdeaStore.

Sources:
  - Scans (.tex files with \\begin{idea}...\\end{idea} blocks)
  - Idea JSONs (from extract_ideas pipeline)
  - Manual text input
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from vbagent.ideas.models import Idea
from vbagent.ideas.store import IdeaStore


def collect_from_scans(
    store: IdeaStore,
    scans_dir: Path,
    subject: str = "physics",
) -> tuple[int, int]:
    """Extract ideas from scan .tex files and add to store.

    Parses \\begin{idea}...\\end{idea} blocks, extracts topic hints
    and formulas, then adds to store with deduplication.

    Returns (new_count, duplicate_count).
    """
    ideas: list[Idea] = []

    if not scans_dir.exists():
        return 0, 0

    for f in sorted(scans_dir.glob("*.tex")):
        content = f.read_text()
        matches = re.findall(
            r"\\begin\{idea\}(.*?)\\end\{idea\}", content, re.DOTALL
        )
        for idea_text in matches:
            idea_text = idea_text.strip()
            topic = _extract_topic(idea_text)
            formulas = _extract_formulas(idea_text)

            ideas.append(Idea(
                text=_extract_concept_name(idea_text),
                formulas=formulas,
                topic=topic,
                subtopic="",
                subject=subject,
                sources=[f.name],
                idea_latex=idea_text,
            ))

    return store.add_many(ideas)


def collect_from_ideas_dir(
    store: IdeaStore,
    ideas_dir: Path,
    subject: str = "physics",
) -> tuple[int, int]:
    """Collect ideas from JSON files (IdeaResult format).

    Returns (new_count, duplicate_count).
    """
    ideas: list[Idea] = []

    if not ideas_dir.exists():
        return 0, 0

    for f in sorted(ideas_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        # Handle IdeaResult format
        idea_list = data.get("ideas", [])
        if isinstance(idea_list, list):
            for item in idea_list:
                if isinstance(item, str):
                    ideas.append(Idea(
                        text=item,
                        topic=data.get("topic", ""),
                        subject=subject,
                        sources=[f.name],
                    ))
                elif isinstance(item, dict):
                    ideas.append(Idea(
                        text=item.get("text", item.get("idea", "")),
                        formulas=item.get("formulas", []),
                        topic=item.get("topic", data.get("topic", "")),
                        subtopic=item.get("subtopic", ""),
                        subject=subject,
                        sources=[f.name],
                        idea_latex=item.get("idea_latex", ""),
                    ))

        # Also check top-level fields
        if "topic" in data and "ideas" not in data:
            ideas.append(Idea(
                text=data.get("topic", ""),
                formulas=data.get("formulas", []),
                topic=data.get("topic", ""),
                subject=subject,
                sources=[f.name],
                idea_latex=data.get("idea_latex", ""),
            ))

    return store.add_many(ideas)


def collect_manual(
    store: IdeaStore,
    text: str,
    topic: str,
    formulas: list[str] | None = None,
    subject: str = "physics",
) -> tuple[Idea, bool]:
    """Add a single idea manually.

    Returns (idea, is_new).
    """
    idea = Idea(
        text=text,
        formulas=formulas or [],
        topic=topic,
        subject=subject,
        sources=["manual"],
    )
    return store.add(idea)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_topic(idea_text: str) -> str:
    """Extract topic from idea LaTeX content."""
    # Pattern: \textbf{Concept:} ...
    m = re.search(r"\\textbf\{Concept:\}\s*(.+?)(?:\\\\|$|\})", idea_text)
    if m:
        return m.group(1).strip().rstrip("}")

    # Pattern: \intertext{\textbf{...}}
    m = re.search(r"\\intertext\{(.+?)\}", idea_text)
    if m:
        topic = m.group(1).strip()
        topic = re.sub(r"\\textbf\{(.*?)\}", r"\1", topic)
        return topic

    return ""


def _extract_concept_name(idea_text: str) -> str:
    """Extract a short concept name from idea text."""
    topic = _extract_topic(idea_text)
    if topic:
        return topic

    # Fallback: first non-empty line, stripped of LaTeX
    for line in idea_text.split("\n"):
        line = line.strip()
        if line and not line.startswith("\\begin") and not line.startswith("\\end"):
            # Strip LaTeX commands
            clean = re.sub(r"\\[a-zA-Z]+\{?", "", line)
            clean = re.sub(r"[{}\\\$]", "", clean).strip()
            if clean:
                return clean[:100]

    return idea_text[:80]


def _extract_formulas(idea_text: str) -> list[str]:
    """Extract formula strings from idea LaTeX.

    Formulas are stored WITHOUT math delimiters ($, \\[, etc.)
    since they'll be placed inside align* or other math environments.
    """
    formulas = []

    # Inline math: $...$  — extract content without delimiters
    for m in re.finditer(r"\$([^$]+)\$", idea_text):
        formula = m.group(1).strip()
        if len(formula) > 3:  # skip trivial like $x$
            formulas.append(formula)

    # align* content
    for m in re.finditer(
        r"\\begin\{align\*?\}(.*?)\\end\{align\*?\}", idea_text, re.DOTALL
    ):
        # Extract individual lines
        for line in m.group(1).split("\\\\"):
            line = line.strip()
            # Strip any stray $ delimiters inside align*
            line = re.sub(r"^\$|\$$", "", line).strip()
            if not line:
                continue
            if "&" in line:
                # Take the full aligned expression
                formulas.append(line)
            else:
                formulas.append(line)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for f in formulas:
        if f not in seen:
            seen.add(f)
            unique.append(f)

    return unique[:10]  # cap at 10
