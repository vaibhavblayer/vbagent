import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from vbagent.authoring.application import ArtifactResult, AuthoringApplication
from vbagent.mcp.server import SERVER_INSTRUCTIONS, MCPServer


@pytest.mark.asyncio
async def test_draft_resource_never_claims_to_be_validated(tmp_path, monkeypatch):
    app = AuthoringApplication(tmp_path)
    monkeypatch.setattr(app, "get_final_artifact", lambda *_: ArtifactResult(
        run_id="run", spec_id="item", path=str(tmp_path / "problem_1.tex"),
        content=r"\item A draft question", status="draft", validated=False, number=1,
    ))
    resources = list(await MCPServer(application=app).server.read_resource(
        "vbagent://authoring/runs/run/items/item/final"
    ))
    assert resources[0].content.startswith("% VBAgent artifact status: draft; validated=false\n")
    assert resources[0].mime_type == "text/x-tex"


@pytest.mark.asyncio
async def test_authoring_mcp_exposes_typed_tools_annotations_and_structured_errors(tmp_path):
    server = MCPServer(application=AuthoringApplication(tmp_path))

    tools = await server.list_tools()
    by_name = {tool.name: tool for tool in tools}

    assert set(by_name) == {
        "authoring_list_catalogs",
        "authoring_search_catalog",
        "authoring_inspect_catalog",
        "authoring_list_topics",
        "authoring_plan",
        "authoring_start",
        "authoring_status",
        "authoring_list_items",
        "authoring_cancel",
        "authoring_resume",
        "authoring_review",
        "authoring_plan_variants",
        "authoring_read_final",
        "authoring_read_evidence",
        "authoring_read_worker_log",
    }
    assert all(tool.outputSchema for tool in tools)
    assert by_name["authoring_status"].annotations.readOnlyHint is True
    assert by_name["authoring_start"].annotations.openWorldHint is True
    assert by_name["authoring_cancel"].annotations.destructiveHint is True
    assert by_name["authoring_review"].annotations.destructiveHint is True
    assert "confirmed" in by_name["authoring_start"].inputSchema["properties"]
    public_intent = by_name["authoring_plan"].inputSchema["$defs"]["AuthoringIntent"]
    assert "syllabus_path" not in public_intent["properties"]
    assert "existing_accepted_counts" not in public_intent["properties"]
    assert "variant_parent_latex" not in public_intent["properties"]
    assert {"include_solution", "include_idea"} <= public_intent["properties"].keys()
    assert {"complete_run_id", "complete_spec_ids"} <= by_name["authoring_plan"].inputSchema["properties"].keys()
    assert "rebuild_only" in by_name["authoring_start"].inputSchema["properties"]
    assert "problem_numbers" in by_name["authoring_start"].inputSchema["properties"]
    assert "decision" in by_name["authoring_review"].inputSchema["properties"]
    assert "Planning is deterministic" in SERVER_INSTRUCTIONS
    assert "compact matches" in SERVER_INSTRUCTIONS

    catalogs = await server.call_tool("authoring_list_catalogs", {})
    assert catalogs.isError is False
    assert catalogs.structuredContent["ok"] is True
    catalog_data = catalogs.structuredContent["data"]
    assert catalog_data["total"] == 6
    assert {
        (item["exam"], item["subject"])
        for item in catalog_data["catalogs"]
    } == {
        ("jee_main", "chemistry"),
        ("jee_main", "mathematics"),
        ("jee_main", "physics"),
        ("neet", "biology"),
        ("neet", "chemistry"),
        ("neet", "physics"),
    }

    search = await server.call_tool(
        "authoring_search_catalog",
        {
            "exam": "jee_main",
            "subject": "mathematics",
            "query": "greatest integer function",
        },
    )
    assert search.isError is False
    assert search.structuredContent["data"]["total"] == 1
    assert search.structuredContent["data"]["matches"][0] == {
        "kind": "topic",
        "chapter_id": "jee_main.mathematics.limit-continuity-and-differentiability",
        "chapter": "LIMIT, CONTINUITY AND DIFFERENTIABILITY",
        "topic_id": (
            "jee_main.mathematics.limit-continuity-and-differentiability.topic-001"
        ),
        "topic": (
            "Real-valued functions, algebra of functions and graphs of simple functions"
        ),
        "aliases": [
            "algebra of functions",
            "floor function",
            "gif",
            "graphs of simple functions",
            "greatest integer",
            "greatest integer function",
            "modulus function",
            "real valued functions",
            "signum function",
        ],
        "description": (
            "Official scope: real-valued functions, their algebra, and graphs of simple "
            "functions. Narrow function requests should also be retained as required concepts."
        ),
    }
    assert search.structuredContent["data"]["allowed_question_types"] == [
        "mcq_sc",
        "integer",
    ]

    inspection = await server.call_tool(
        "authoring_inspect_catalog",
        {"exam": "jee_main", "subject": "mathematics"},
    )
    assert inspection.isError is False
    chapters = inspection.structuredContent["data"]["chapters"]
    assert len(chapters) == 14
    assert all("topics" not in chapter for chapter in chapters)
    assert chapters[6]["topic_count"] == 12

    topic_page = await server.call_tool(
        "authoring_list_topics",
        {
            "exam": "jee_main",
            "subject": "mathematics",
            "chapter": "limit continuity and differentiability",
            "offset": 0,
            "limit": 2,
        },
    )
    assert topic_page.isError is False
    page_data = topic_page.structuredContent["data"]
    assert page_data["chapter"] == "LIMIT, CONTINUITY AND DIFFERENTIABILITY"
    assert page_data["total"] == 12
    assert len(page_data["topics"]) == 2
    assert page_data["next_offset"] == 2

    missing = await server.call_tool("authoring_status", {"run_id": "missing"})
    assert missing.isError is True
    assert missing.structuredContent == {
        "ok": False,
        "data": None,
        "error": {
            "code": "not_found",
            "message": "unknown authoring run: missing",
            "details": [],
        },
    }

    invalid = await server.call_tool(
        "authoring_plan",
        {
            "intent": {
                "exam": "jee_main",
                "subject": "physics",
                "chapter": "kinematics",
                "question_types": {"invented_type": 1},
            }
        },
    )
    assert invalid.isError is True
    assert invalid.structuredContent["error"]["code"] == "validation_error"
    assert invalid.structuredContent["error"]["details"][0]["loc"] == [
        "question_types"
    ]


@pytest.mark.asyncio
async def test_authoring_mcp_plan_is_durable_and_start_requires_confirmation(tmp_path):
    server = MCPServer(application=AuthoringApplication(tmp_path))
    arguments = {
        "intent": {
            "exam": "jee_main",
            "subject": "physics",
            "chapter": "kinematics",
            "topics": ["projectile motion"],
            "count": 2,
            "question_types": {"mcq_sc": 1},
            "difficulties": {"5": 1},
            "seed": 23,
        },
        "max_attempts": 2,
        "concurrency": 3,
    }

    planned = await server.call_tool("authoring_plan", arguments)
    assert planned.isError is False
    data = planned.structuredContent["data"]
    assert data["total_items"] == 2
    assert data["status"] == "pending"
    assert data["requires_confirmation"] is True

    refused = await server.call_tool(
        "authoring_start",
        {"run_id": data["run_id"], "confirmed": False},
    )
    assert refused.isError is True
    assert refused.structuredContent["error"]["code"] == "invalid_request"
    assert "explicit user authorization" in refused.structuredContent["error"]["message"]

    items = await server.call_tool(
        "authoring_list_items",
        {"run_id": data["run_id"], "limit": 1},
    )
    assert items.isError is False
    assert items.structuredContent["data"]["total"] == 2
    assert len(items.structuredContent["data"]["items"]) == 1
    assert "candidate" not in items.structuredContent["data"]["items"][0] or (
        items.structuredContent["data"]["items"][0]["candidate"] is None
    )

    spec_id = items.structuredContent["data"]["items"][0]["spec_id"]
    unpublished = await server.call_tool(
        "authoring_read_final",
        {"run_id": data["run_id"], "spec_id": spec_id},
    )
    assert unpublished.isError is True
    assert unpublished.structuredContent["error"]["code"] == "invalid_request"

    evidence = await server.call_tool(
        "authoring_read_evidence",
        {"run_id": data["run_id"], "spec_id": spec_id},
    )
    assert evidence.isError is False
    assert evidence.structuredContent["data"]["evidence"]["status"] == "pending"

    worker_log = await server.call_tool(
        "authoring_read_worker_log",
        {"run_id": data["run_id"], "offset": 0},
    )
    assert worker_log.isError is False
    assert worker_log.structuredContent["data"]["content"] == ""


@pytest.mark.asyncio
async def test_real_stdio_handshake_keeps_stdout_protocol_clean(tmp_path):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "vbagent.cli.main",
            "mcp",
            "--output",
            str(tmp_path),
        ],
    )

    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        initialized = await session.initialize()
        assert initialized.serverInfo.name == "vbagent-authoring"
        assert "Use authoring_plan first" in initialized.instructions

        tools = await session.list_tools()
        assert len(tools.tools) == 15
        assert all(tool.outputSchema for tool in tools.tools)

        catalogs = await session.call_tool("authoring_list_catalogs", {})
        assert catalogs.isError is False
        assert catalogs.structuredContent["ok"] is True

        domain_error = await session.call_tool(
            "authoring_inspect_catalog",
            {"exam": "missing_exam", "subject": "physics"},
        )
        assert domain_error.isError is True
        assert domain_error.structuredContent["error"]["code"] == "not_found"

        templates = await session.list_resource_templates()
        assert len(templates.resourceTemplates) == 2
