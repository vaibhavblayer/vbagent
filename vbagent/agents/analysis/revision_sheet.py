"""Agent for generating concise revision sheets."""

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agent

from pydantic import BaseModel, Field

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.analysis.revision_sheet import get_revision_sheet_prompt


# ---------------------------------------------------------------------------
# Pydantic models — one latex block per topic
# ---------------------------------------------------------------------------

class RevisionTopic(BaseModel):
    """A syllabus topic with its complete itemize block of core ideas."""
    topic_name: str = Field(description="Syllabus topic name")
    latex: str = Field(
        description="Complete \\begin{itemize}...\\end{itemize} block with all core ideas for this topic",
    )


class RevisionSheet(BaseModel):
    """Complete revision sheet for a chapter."""
    topics: list[RevisionTopic] = Field(description="Topics with their LaTeX blocks")


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_key(raw_ideas: dict, syllabus_topics: list[str], chapter_name: str) -> str:
    data = {"chapter": chapter_name, "topics": syllabus_topics, "ideas": raw_ideas, "_mode": "brief_v4"}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _cache_path(key: str) -> Path:
    d = Path(".vbagent/cache/analysis")
    d.mkdir(parents=True, exist_ok=True)
    return d / f"brief_{key}.json"


def _load_cache(key: str) -> dict | None:
    p = _cache_path(key)
    if p.exists():
        try:
            return json.load(open(p, "r", encoding="utf-8"))
        except Exception:
            return None
    return None


def _save_cache(key: str, data: dict):
    try:
        json.dump(data, open(_cache_path(key), "w", encoding="utf-8"), indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_revision_sheet(
    raw_ideas: dict,
    syllabus_topics: list[str],
    chapter_name: str,
    exam: str = "jee_main",
    subject: str = "physics",
    show_spinner: bool = True,
    no_cache: bool = False,
) -> dict:
    """Generate a concise revision sheet using an AI agent.

    Returns:
        {topic_name: latex_string, ...}
    """
    if not no_cache:
        key = _cache_key(raw_ideas, syllabus_topics, chapter_name)
        cached = _load_cache(key)
        if cached:
            return cached

    agent_input = _build_input(raw_ideas, syllabus_topics, chapter_name, exam, subject)

    agent = create_agent(
        name="RevisionSheetGenerator",
        instructions=get_revision_sheet_prompt(),
        output_type=RevisionSheet,
        agent_type="idea",
    )

    result: RevisionSheet = run_agent_sync(agent, agent_input, show_spinner=show_spinner)

    organized = {topic.topic_name: topic.latex for topic in result.topics}

    if not no_cache:
        key = _cache_key(raw_ideas, syllabus_topics, chapter_name)
        _save_cache(key, organized)

    return organized


# ---------------------------------------------------------------------------
# Input builder
# ---------------------------------------------------------------------------

def _build_input(
    raw_ideas: dict,
    syllabus_topics: list[str],
    chapter_name: str,
    exam: str,
    subject: str,
) -> str:
    from vbagent.analysis.templates import load_chapter_template, format_template_for_agent

    text = f"# Chapter: {chapter_name}\n\n## Syllabus Topics\n"
    for i, topic in enumerate(syllabus_topics, 1):
        text += f"{i}. {topic}\n"

    template = load_chapter_template(exam, subject, chapter_name)
    if template:
        text += "\n" + format_template_for_agent(template)

    text += "\n## Problems from Exam\n\n"

    problems_list = raw_ideas.get("all_problems", {}).get("problems", [])
    if not problems_list:
        text += "(No problems found)\n"
        return text

    for problem in problems_list:
        num = problem["problem_num"]
        text += f"### Problem {num}\n\n"
        if problem.get("question"):
            text += f"**Question:**\n{problem['question']}\n\n"
        if problem.get("solution"):
            text += f"**Solution:**\n{problem['solution']}\n\n"
        if problem.get("concepts") or problem.get("formulas") or problem.get("techniques"):
            text += "**Extracted Ideas:**\n"
            for c in problem.get("concepts", []):
                text += f"- {c}\n"
            for f in problem.get("formulas", []):
                text += f"- {f}\n"
            for t in problem.get("techniques", []):
                text += f"- {t}\n"
            text += "\n"
        text += "---\n\n"

    return text
