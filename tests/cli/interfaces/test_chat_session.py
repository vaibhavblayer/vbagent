import asyncio
import json
import threading
from types import SimpleNamespace

import pytest
from agents import FunctionTool, ToolSearchTool

from vbagent.authoring.application import (
    AuthoringIntent,
    RunCommandResult,
    WorkerLaunch,
)
from vbagent.authoring.results import (
    REQUIRED_ACCEPTANCE_GATES,
    AuthoredCandidate,
    CandidateStatus,
    GateResult,
)
from vbagent.authoring.store import AuthoringStore
from vbagent.mcp.chat import AuthoringChatSession, LatestRunState


def _session(tmp_path, **kwargs):
    return AuthoringChatSession(
        tmp_path,
        model="gpt-5.6-luna",
        mirror_worker_io=False,
        **kwargs,
    )


def _plan(session):
    payload = session.call_tool("authoring_plan", {
        "intent": {"exam": "jee_main", "subject": "physics",
                   "chapter": "kinematics", "topics": ["projectile motion"], "count": 1},
    })
    assert payload["ok"]
    return payload["data"]["run_id"]


def _controller(monkeypatch, callback):
    def run(_agent, _input, _group, **_kwargs):
        callback()
        return SimpleNamespace(final_output="Done.", response_id="resp-test", credentials=None)

    monkeypatch.setattr("vbagent.agents.base.run_agent_sync_continued", run)


@pytest.mark.parametrize("effort", [None, "medium", "high", "low"])
def test_chat_defaults_to_medium_and_honors_reasoning_override(tmp_path, effort):
    session = _session(tmp_path, reasoning_effort=effort)
    expected = effort or "medium"
    assert session.reasoning_effort == expected
    assert session.agent.model_settings.reasoning.effort == expected


def test_direct_start_is_authorized_in_the_same_controller_turn(tmp_path, monkeypatch):
    approvals, launches, results = [], [], []
    session = _session(tmp_path, approval_handler=lambda *args: approvals.append(args))
    run_id = _plan(session)

    def launch(root, run, *_args):
        launches.append(run)
        return WorkerLaunch(pid=4321, log_path=str(root / "worker.log"))

    session.server.application.launcher = launch
    _controller(monkeypatch, lambda: results.append(session.call_tool(
        "authoring_start", {"run_id": run_id, "confirmed": True},
    )))
    session.send("Please start this run now", show_spinner=False)

    assert results[0]["ok"]
    assert launches == [run_id]
    assert approvals == []
    assert session.pending_approval() is None
    # No permission survives the request or authorizes a different action.
    result = session.call_tool("authoring_cancel", {"run_id": run_id})
    assert result["error"]["code"] == "approval_required"


def test_creation_authority_binds_to_a_plan_from_that_turn(tmp_path, monkeypatch):
    session = _session(tmp_path, approval_handler=lambda *_args: None)
    old_run = _plan(session)
    _controller(monkeypatch, lambda: None)
    session.send("Create a new mathematics problem", show_spinner=False)
    assert session.pending_run_id is None
    assert session.server.application.status(old_run).status == "pending"
    assert session.authorized_pending_run_id is None

    _controller(monkeypatch, lambda: _plan(session))
    session.send("Create one projectile motion problem", show_spinner=False)
    assert session.authorized_pending_run_id == session.pending_run_id


@pytest.mark.parametrize("message", [
    "Plan one problem", "How can this generate problems?", "Don't generate any problems",
])
def test_non_creation_requests_cannot_auto_start_a_plan(tmp_path, monkeypatch, message):
    session = _session(tmp_path, approval_handler=lambda *_args: None)
    _controller(monkeypatch, lambda: _plan(session))
    session.send(message, show_spinner=False)
    assert session.pending_run_id is not None
    assert session.authorized_pending_run_id is None
    assert "Reply yes or no" in session.pending_approval()["question"]


def test_approval_first_in_words_overrides_blanket_auto_approval(tmp_path, monkeypatch):
    session = _session(tmp_path, approval_handler=lambda *_args: True)
    run_id = _plan(session)
    results = []
    _controller(monkeypatch, lambda: results.append(session.call_tool(
        "authoring_start", {"run_id": run_id, "confirmed": True},
    )))
    session.send("Show me the plan before you start", show_spinner=False)
    assert results[0]["error"]["code"] == "approval_required"
    assert session.server.application.status(run_id).worker is None


def test_tool_proposals_cannot_silently_replace_each_other(tmp_path):
    session = _session(tmp_path, approval_handler=lambda *_args: None)
    run_id = _plan(session)
    session.call_tool("authoring_cancel", {"run_id": run_id})
    session.call_tool("authoring_start", {"run_id": run_id, "confirmed": True})
    assert session.pending_tool_name == "authoring_cancel"
    assert "Cancel" in session.pending_approval()["question"]
    assert session.approve_pending_action()["data"]["action"] == "cancel"
    assert session.pending_approval() is None


def test_pending_question_never_uses_a_different_runs_scope(tmp_path):
    session = _session(tmp_path)
    run_id = _plan(session)
    session._latest_run_state = LatestRunState("other-run", "pending", topics=("Unrelated",))
    assert session.pending_approval()["run"] == {"run_id": run_id}


def test_new_tool_question_does_not_leave_an_old_plan_behind(tmp_path):
    session = _session(tmp_path, approval_handler=lambda *_args: None)
    _plan(session)
    session.call_tool("authoring_cancel", {"run_id": "another-run"})
    session.decline_pending_action()
    assert session.pending_approval() is None


def test_invalid_compile_arguments_return_a_tool_error_not_a_chat_crash(tmp_path, monkeypatch):
    session = _session(tmp_path)
    run_id = _plan(session)
    results = []
    _controller(monkeypatch, lambda: results.append(session.call_tool("authoring_start", {
        "run_id": run_id, "confirmed": True, "rebuild_only": True, "problem_numbers": 6,
    })))
    session.send("Only include problems 6 and 7", show_spinner=False)
    assert results[0]["error"]["code"] == "invalid_arguments"


def test_single_turn_explicit_intent_remains_opt_in(tmp_path, monkeypatch):
    session = _session(tmp_path, allow_intent_actions=False, approval_handler=lambda *_args: False)
    results = []
    run_id = _plan(session)
    _controller(monkeypatch, lambda: results.append(session.call_tool(
        "authoring_start", {"run_id": run_id, "confirmed": True},
    )))
    session.send("Start this run", show_spinner=False)
    assert results[0]["error"]["code"] == "user_declined"
    assert session.authorized_pending_run_id is None


@pytest.mark.parametrize("target", ["different-run", "authoring_cancel"])
def test_direct_start_does_not_grant_another_run_or_action(tmp_path, monkeypatch, target):
    session = _session(tmp_path, approval_handler=lambda *_args: None)
    run_id = _plan(session)
    results = []
    tool = "authoring_cancel" if target == "authoring_cancel" else "authoring_start"
    arguments = {"run_id": run_id if tool == "authoring_cancel" else target}
    if tool == "authoring_start":
        arguments["confirmed"] = True
    _controller(monkeypatch, lambda: results.append(session.call_tool(tool, arguments)))
    session.send("Start this run now", show_spinner=False)
    assert results[0]["error"]["code"] == "approval_required"
    assert session.server.application.status(run_id).worker is None


@pytest.mark.parametrize("numbers", [[6, 7], None, [1, 2], [7, 6]])
def test_explicit_subset_rebuild_needs_no_reapproval_but_must_match(tmp_path, monkeypatch, numbers):
    approvals, rebuilds, results = [], [], []
    session = _session(tmp_path, approval_handler=lambda *args: approvals.append(args))
    run_id = _plan(session)

    def rebuild(run, **kwargs):
        rebuilds.append(kwargs)
        return RunCommandResult(
            run_id=run, action="rebuild", dispatched=False,
            status=session.server.application.status(run), message="Compiled existing files.",
        )

    monkeypatch.setattr(session.server.application, "start", rebuild)
    arguments = {"run_id": run_id, "confirmed": True, "rebuild_only": True}
    if numbers is not None:
        arguments["problem_numbers"] = numbers
    _controller(monkeypatch, lambda: results.append(session.call_tool("authoring_start", arguments)))
    session.send("onlt include last two modulus problem, 6, 7", show_spinner=False)

    assert approvals == []
    if numbers == [6, 7]:
        assert results[0]["ok"]
        assert rebuilds[0]["problem_numbers"] == [6, 7]
        assert session.pending_tool_name is None
    else:
        assert results[0]["error"]["code"] in {"problem_selection_required", "problem_selection_mismatch"}
        assert rebuilds == []
    assert session.authorized_pending_run_id is None


def test_compile_after_completion_does_not_start_or_rebuild_pending_run(tmp_path, monkeypatch):
    session = _session(tmp_path, approval_handler=lambda *_args: True)
    run_id = _plan(session)
    results = []

    def calls():
        for rebuild in (False, True):
            results.append(session.call_tool("authoring_start", {
                "run_id": run_id, "confirmed": True, "rebuild_only": rebuild,
            }))

    _controller(monkeypatch, calls)
    session.send("copile this to main.tex and pdf after completion", show_spinner=False)

    assert [result["error"]["code"] for result in results] == [
        "generation_not_requested", "automatic_compilation_pending",
    ]
    assert session.server.application.status(run_id).worker is None
    assert session.pending_tool_name is None
    assert session.authorized_pending_run_id is None
    assert session.pending_approval()["action"] == "start_background_generation"


def test_one_plain_approval_handles_staged_start_and_plan(tmp_path):
    launches = []
    session = _session(tmp_path, approval_handler=lambda *_args: None)
    run_id = _plan(session)

    def launch(root, run, *_args):
        launches.append(run)
        return WorkerLaunch(pid=4321, log_path=str(root / "worker.log"))

    session.server.application.launcher = launch
    staged = session.call_tool("authoring_start", {"run_id": run_id, "confirmed": True})
    assert "Reply yes or no" in staged["error"]["message"]
    assert "/approve" not in staged["error"]["message"]
    approved = session.approve_pending_action()
    assert approved["ok"]
    assert launches == [run_id]
    assert session.pending_approval() is None


def test_declining_start_also_clears_plan_without_cancelling_it(tmp_path):
    session = _session(tmp_path, approval_handler=lambda *_args: None)
    run_id = _plan(session)
    session.call_tool("authoring_start", {"run_id": run_id, "confirmed": True})
    session.decline_pending_action()
    assert session.pending_approval() is None
    assert session.server.application.status(run_id).status == "pending"


def test_next_controller_turn_sees_locally_updated_state(tmp_path, monkeypatch):
    session = _session(tmp_path)
    run_id = _plan(session)
    session._latest_run_state = LatestRunState(run_id, "running", worker_status="started")
    session._pending_run_confirmation = None
    inputs = []

    def run(_agent, input_data, _group, **_kwargs):
        inputs.append(input_data)
        return SimpleNamespace(final_output="Running.", response_id="resp-test", credentials=None)

    monkeypatch.setattr("vbagent.agents.base.run_agent_sync_continued", run)
    session.send("What is the status?", show_spinner=False)
    assert inputs[0][0]["role"] == "developer"
    assert '"worker_status": "started"' in inputs[0][0]["content"]
    assert '"pending_run_id": null' in inputs[0][0]["content"]


def test_chat_tools_are_discovered_from_fastmcp_and_emit_complete_traces(tmp_path):
    events = []
    session = _session(tmp_path, trace_sink=events.append)

    tool = next(
        item for item in session.agent.tools if item.name == "authoring_list_catalogs"
    )
    result = asyncio.run(tool.on_invoke_tool(None, "{}"))
    payload = json.loads(result)

    assert payload["ok"] is True
    assert payload["data"]["total"] >= 2
    assert [event.phase for event in events] == ["input", "output"]
    assert events[0].payload == {}
    assert events[1].payload == payload
    assert set(session.tool_names) == {
        item.name for item in asyncio.run(session.server.list_tools())
    }


def test_chat_defers_server_controller_and_namespaced_tool_schemas(tmp_path):
    session = _session(tmp_path)

    assert session.server_ready is False
    assert session.controller_ready is False

    session.prepare_controller()

    assert session.server_ready is True
    assert session.controller_ready is True
    assert isinstance(session.agent.tools[0], ToolSearchTool)
    functions = [
        tool for tool in session.agent.tools if isinstance(tool, FunctionTool)
    ]
    assert len(functions) == 15
    assert all(tool.defer_loading for tool in functions)
    assert {
        tool.qualified_name.split(".", 1)[0] for tool in functions
    } == {"syllabus_authoring", "authoring_runs"}


def test_chat_applies_a_local_approval_gate_before_consequential_tools(tmp_path):
    events = []
    session = _session(
        tmp_path,
        trace_sink=events.append,
        approval_handler=lambda _name, _arguments: False,
    )
    planned = session.server.application.plan(
        AuthoringIntent(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            count=1,
        )
    )
    start = next(
        item for item in session.agent.tools if item.name == "authoring_start"
    )

    result = asyncio.run(
        start.on_invoke_tool(
            None,
            json.dumps({"run_id": planned.run_id, "confirmed": True}),
        )
    )
    payload = json.loads(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "user_declined"
    assert session.server.application.status(planned.run_id).worker is None
    assert [event.phase for event in events] == ["input", "error"]


def test_chat_stages_approval_instead_of_blocking_inside_model_tool(tmp_path):
    session = _session(
        tmp_path,
        approval_handler=lambda _name, _arguments: None,
    )
    planned = session.server.application.plan(
        AuthoringIntent(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            count=1,
        )
    )
    cancel = next(
        item for item in session.agent.tools if item.name == "authoring_cancel"
    )

    staged = json.loads(
        asyncio.run(
            cancel.on_invoke_tool(
                None,
                json.dumps({"run_id": planned.run_id, "reason": "operator request"}),
            )
        )
    )

    assert staged["error"]["code"] == "approval_required"
    assert session.pending_tool_name == "authoring_cancel"
    assert session.server.application.status(planned.run_id).status == "pending"

    approved = session.approve_pending_tool()
    assert approved["ok"] is True
    assert session.pending_tool_name is None
    assert session.server.application.status(planned.run_id).status == "cancelled"


def test_chat_confirm_starts_latest_plan_without_second_approval_or_model_turn(tmp_path):
    approvals = []
    launches = []
    session = _session(
        tmp_path,
        approval_handler=lambda name, arguments: approvals.append((name, arguments))
        or False,
    )

    def launcher(output_root, run_id, concurrency, resume, dispatch_token):
        launches.append((run_id, concurrency, resume, dispatch_token))
        return WorkerLaunch(
            pid=4321,
            log_path=str(output_root / "runs" / run_id / "worker.log"),
        )

    session.server.application.launcher = launcher
    plan = next(item for item in session.agent.tools if item.name == "authoring_plan")
    planned = json.loads(
        asyncio.run(
            plan.on_invoke_tool(
                None,
                json.dumps(
                    {
                        "intent": {
                            "exam": "jee_main",
                            "subject": "physics",
                            "chapter": "kinematics",
                            "topics": ["projectile motion"],
                            "count": 1,
                        },
                        "concurrency": 2,
                    }
                ),
            )
        )
    )

    assert session.pending_run_id == planned["data"]["run_id"]
    latest = session.latest_run_state
    assert latest.status == "pending"
    assert latest.current_stage == "awaiting_start"
    assert latest.chapters == ("KINEMATICS",)
    assert latest.topics == ("Motion in a plane, Projectile Motion",)
    assert planned["data"]["run_id"][:12] in session.latest_run_label
    assert "awaiting start" in session.latest_run_label
    approval = session.pending_background_approval()
    assert approval["action"] == "start_background_generation"
    assert approval["run"]["topics"] == [
        "Motion in a plane, Projectile Motion"
    ]
    assert "background" in approval["question"]
    started = session.confirm_pending_run()

    assert started["ok"] is True
    assert started["data"]["dispatched"] is True
    assert started["data"]["worker"]["pid"] == 4321
    assert launches[0][1:3] == (2, False)
    assert approvals == []
    assert session.pending_run_id is None


def test_chat_completion_returns_full_code_and_exact_generated_path_once(tmp_path):
    session = _session(tmp_path)
    plan_tool = next(
        item for item in session.agent.tools if item.name == "authoring_plan"
    )
    planned = json.loads(
        asyncio.run(
            plan_tool.on_invoke_tool(
                None,
                json.dumps(
                    {
                        "intent": {
                            "exam": "jee_main",
                            "subject": "physics",
                            "chapter": "kinematics",
                            "topics": ["projectile motion"],
                            "count": 1,
                        }
                    }
                ),
            )
        )
    )["data"]

    with AuthoringStore(tmp_path) as store:
        claimed = store.claim_next(planned["run_id"], "test-worker")
        problem = (
            r"\item A projectile has range"
            "\n"
            r"\begin{tasks}(2)\task $R$ \ans\task $2R$\task $R/2$\task $0$\end{tasks}"
        )
        final = problem + "\n" + r"\begin{solution}The range is $R$.\end{solution}"
        candidate = AuthoredCandidate(
            spec=claimed.spec,
            status=CandidateStatus.ACCEPTED,
            problem_latex=problem,
            draft_solution_latex=r"\begin{solution}The range is $R$.\end{solution}",
            independent_solution_latex=(
                r"\begin{solution}The range is $R$.\end{solution}"
            ),
            final_latex=final,
            gates=[
                GateResult(gate=gate, passed=True)
                for gate in REQUIRED_ACCEPTANCE_GATES
            ],
        )
        artifact_dir, digest = store.write_candidate_artifacts(claimed, candidate)
        store.record_candidate(
            claimed,
            candidate,
            artifact_dir=artifact_dir,
            artifact_sha256=digest,
        )

    completion = session.take_completion(planned["run_id"])

    assert completion["event"] == "generation_completed"
    assert completion["saved_to"] == planned["generated_output_dir"]
    assert completion["manifest_path"].endswith("manifest.json")
    assert completion["artifacts"][0]["content"] == final + "\n"
    assert completion["artifacts"][0]["path"].endswith(".tex")
    assert session.take_completion(planned["run_id"]) is None


def test_chat_asks_for_author_decision_when_checks_are_exhausted(tmp_path):
    session = _session(tmp_path)
    planned = session.server.application.plan(
        AuthoringIntent(exam="jee_main", subject="physics", chapter="kinematics"),
        max_attempts=1,
    )
    with AuthoringStore(tmp_path) as store:
        claimed = store.claim_next(planned.run_id, "test-worker")
        candidate = AuthoredCandidate(
            spec=claimed.spec,
            status=CandidateStatus.REJECTED,
            problem_latex=r"\item Draft needing an author decision",
            final_latex=r"\item Draft needing an author decision",
            gates=[GateResult(gate="spec_alignment", passed=False, summary="requested method missing")],
        )
        folder, digest = store.write_candidate_artifacts(claimed, candidate)
        store.record_candidate(claimed, candidate, artifact_dir=folder, artifact_sha256=digest)
    completion = session.take_completion(planned.run_id)
    assert "Keep for later, revise" in completion["review_prompt"]
    assert completion["accepted_artifacts"] == 0
    assert completion["review_items"][0]["status"] == "needs_review"
    assert completion["artifacts"][0]["validated"] is False
    assert completion["artifacts"][0]["path"].endswith("problem_1.tex")
    assert "requested method missing" in completion["review_items"][0]["human_review_reason"]


def test_chat_latest_label_refreshes_durable_stage_without_another_message(tmp_path):
    session = _session(tmp_path)
    planned = session.server.application.plan(
        AuthoringIntent(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            count=1,
        )
    )

    with AuthoringStore(tmp_path) as store:
        assert store.acquire_run_lease(planned.run_id, "run-owner")
        claimed = store.claim_next(planned.run_id, "worker-a")
        assert store.set_item_stage(claimed, "reviewing_quality")

    state = session.refresh_run_state(planned.run_id)

    assert state.status == "running"
    assert state.current_stage == "reviewing_quality"
    assert state.stage_counts == {"reviewing_quality": 1}
    assert state.active_stages[0]["topic"] == "Motion in a plane, Projectile Motion"
    assert "reviewing quality" in session.latest_run_label


def test_chat_continues_one_response_chain_and_retains_local_history(
    tmp_path,
    monkeypatch,
):
    session = _session(tmp_path)
    calls = []
    credentials = SimpleNamespace(key_name="profile-a")
    responses = iter(
        [
            SimpleNamespace(
                final_output="First answer",
                response_id="resp-1",
                credentials=credentials,
            ),
            SimpleNamespace(
                final_output="Second answer",
                response_id="resp-2",
                credentials=credentials,
            ),
        ]
    )

    def fake_run(agent, input_data, group_id, **kwargs):
        calls.append((agent, input_data, group_id, kwargs))
        return next(responses)

    monkeypatch.setattr(
        "vbagent.agents.base.run_agent_sync_continued",
        fake_run,
    )

    assert session.send("Plan one problem", show_spinner=False) == "First answer"
    assert session.send("Show the plan", show_spinner=False) == "Second answer"

    assert calls[0][1] == "Plan one problem"
    assert calls[0][3]["previous_response_id"] is None
    assert calls[1][1] == "Show the plan"
    assert calls[1][3]["previous_response_id"] == "resp-1"
    assert calls[1][3]["credentials"] is credentials
    assert session.previous_response_id == "resp-2"


def test_chat_can_page_worker_agent_io_without_replaying_bytes(tmp_path):
    events = []
    session = _session(tmp_path, trace_sink=events.append)
    planned = session.server.application.plan(
        AuthoringIntent(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            count=1,
        )
    )
    log_path = tmp_path / "runs" / planned.run_id / "worker.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("[INPUT] draft\n[OUTPUT] draft\n", encoding="utf-8")

    first = session.read_new_worker_io(planned.run_id)
    second = session.read_new_worker_io(planned.run_id)

    assert first["data"]["content"] == "[INPUT] draft\n[OUTPUT] draft\n"
    assert second["data"]["content"] == ""
    inputs = [event for event in events if event.phase == "input"]
    assert inputs[0].payload["offset"] == 0
    assert inputs[1].payload["offset"] == first["data"]["next_offset"]

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("[INPUT] review\n[OUTPUT] review\n")
    live_page = session.poll_new_worker_io(planned.run_id)

    assert live_page["content"] == "[INPUT] review\n[OUTPUT] review\n"
    assert session.poll_new_worker_io(planned.run_id) is None


def test_latest_toolbar_shows_drafts_checks_retries_and_current_item():
    state = LatestRunState(
        run_id="4bd28fb4fb9c-example",
        status="running",
        total_items=5,
        accepted=1,
        topics=("Earlier topic",),
        current_stage="solving_independently",
        active_stages=({"ordinal": 2, "attempt": 3, "topic": "One-one functions"},),
        progress_counts={"drafted": 3, "checking": 2, "retrying": 2, "accepted": 1},
        latest_failure={"gate": "spec_alignment", "summary": "Missing method"},
    )
    label = state.prompt_label()
    assert "drafted 3/5" in label
    assert "accepted 1/5" in label
    assert "checking 2" in label
    assert "retrying 2" in label
    assert "#2 solving independently (try 3)" in label
    assert "One-one functions" in label
    assert "Earlier topic" not in label
    assert "last: spec alignment" in label
    assert state.as_dict()["progress"]["drafted"] == 3


def test_completion_drains_all_log_pages_before_delivering_final_code(tmp_path, monkeypatch):
    session = _session(tmp_path)
    session.mirror_worker_io = True
    pages = iter([
        {"content": "first page", "eof": False},
        {"content": "last page", "eof": True},
    ])
    monkeypatch.setattr(session, "refresh_run_state", lambda _run: SimpleNamespace(completion_ready=True))
    monkeypatch.setattr(session, "poll_new_worker_io", lambda _run: next(pages))
    monkeypatch.setattr(session, "take_completion", lambda *_args, **_kwargs: {"event": "completed"})
    received = []

    result = session.wait_for_run_completion("run", threading.Event(), worker_io_callback=received.append)

    assert result == {"event": "completed"}
    assert [page["content"] for page in received] == ["first page", "last page"]
