import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from rich.console import Console

from vbagent.cli.interfaces import chat as chat_module
from vbagent.cli.interfaces.chat import (
    ChatPrompt,
    RichChatRenderer,
    _authoring_intent_policy,
    chat,
)
from vbagent.cli.main import main


class FakeSession:
    def __init__(self, output_root="agentic/authoring"):
        self.model = "gpt-5.6-luna"
        self.server = SimpleNamespace(
            application=SimpleNamespace(output_root=Path(output_root).resolve())
        )
        self.messages = []
        self.cleared = False
        self.controller_ready = False
        self.pending_run_id = None
        self.pending_tool_name = None
        self.authorized_pending_run_id = None
        self.confirmed_runs = []
        self.approved_tools = []
        self.latest_run_state = None
        self.latest_run_label = None

    def send(self, message, *, show_spinner=True):
        self.messages.append((message, show_spinner))
        return "I prepared a no-model-call plan."

    def tool_descriptions(self):
        return [("authoring_plan", "Plan a durable authoring run")]

    def prepare_controller(self):
        self.controller_ready = True

    def call_tool(self, name, arguments):
        return {"ok": True, "data": {"run_id": arguments["run_id"]}}

    def read_new_worker_io(self, run_id):
        return {"ok": True, "data": {"run_id": run_id, "content": ""}}

    def clear(self):
        self.cleared = True

    def pending_approval(self):
        if self.pending_tool_name:
            return {
                "event": "approval_required", "action": self.pending_tool_name,
                "run": {"run_id": "proposed-run"},
                "question": "Rebuild main.tex and main.pdf? Reply yes or no.",
            }
        if self.pending_run_id is None:
            return None
        return {
            "event": "approval_required",
            "action": "start_background_generation",
            "run": {"run_id": self.pending_run_id},
            "estimated_agent_calls": 7,
            "question": "Start this generation in the background? Reply yes or no.",
        }

    def confirm_pending_run(self):
        run_id = self.pending_run_id
        self.confirmed_runs.append(run_id)
        self.pending_run_id = None
        return {
            "ok": True,
            "data": {
                "run_id": run_id,
                "action": "start",
                "dispatched": True,
                "worker": {"pid": 4321},
            },
        }

    def confirm_run(self, run_id):
        self.pending_run_id = run_id
        return self.confirm_pending_run()

    def approve_pending_tool(self):
        name = self.pending_tool_name
        self.approved_tools.append(name)
        self.pending_tool_name = None
        return {"ok": True, "data": {"action": name, "message": "approved"}}

    def approve_pending_action(self):
        if self.pending_tool_name:
            return self.approve_pending_tool()
        return self.confirm_pending_run()

    def decline_pending_action(self):
        action = self.pending_tool_name or "start_background_generation"
        self.pending_tool_name = None
        self.pending_run_id = None
        return {"action": action, "run_id": "proposed-run"}

    def decline_pending_tool(self):
        name = self.pending_tool_name
        self.pending_tool_name = None
        return name


def test_chat_help_describes_transparent_mcp_interface():
    result = CliRunner().invoke(chat, ["--help"])

    assert result.exit_code == 0
    assert "complete tool traces" in result.output
    assert "--model" in result.output
    assert "--worker-io" in result.output
    assert "medium" in result.output


def test_chat_intent_policy_distinguishes_creation_from_preflight():
    assert _authoring_intent_policy("Create one kinematics problem") == "create_now"
    assert _authoring_intent_policy("Can you generate 5 NEET MCQs?") == "create_now"
    assert _authoring_intent_policy("Plan 5 NEET problems") == "confirmation_required"
    assert (
        _authoring_intent_policy("Create 5 problems, but show me before you start")
        == "confirmation_required"
    )
    assert _authoring_intent_policy("How can this generate problems?") == "unspecified"


def test_chat_prompt_up_and_down_browse_session_history():
    with create_pipe_input() as pipe_input:
        chat_prompt = ChatPrompt(
            input=pipe_input,
            output=DummyOutput(),
            force_terminal=True,
        )

        pipe_input.send_text("first request\r")
        assert chat_prompt.ask() == "first request"
        pipe_input.send_text("second request\r")
        assert chat_prompt.ask() == "second request"

        pipe_input.send_text("\x1b[A\x1b[A\x1b[B\r")
        assert chat_prompt.ask() == "second request"

        pipe_input.send_text("\x1b[A\x1b[B\r")
        assert chat_prompt.ask() == ""


def test_chat_single_turn_uses_real_session_boundary(monkeypatch, tmp_path):
    fake = FakeSession(tmp_path)
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return fake

    monkeypatch.setattr(chat_module, "_make_session", factory)
    result = CliRunner().invoke(
        chat,
        [
            "--output",
            str(tmp_path),
            "--message",
            "Create two kinematics questions",
            "--no-trace",
        ],
    )

    assert result.exit_code == 0
    assert "VBAgent Authoring Chat" in result.output
    assert "VBAgent:" in result.output
    assert "I prepared a no-model-call plan" in result.output
    assert fake.messages == [("Create two kinematics questions", True)]
    assert captured["output_root"] == str(tmp_path)
    assert captured["mirror_worker_io"] is True
    assert captured["reasoning_effort"] == "medium"
    assert captured["allow_intent_actions"] is False


def test_chat_renders_controller_input_and_output_as_formatted_json(
    monkeypatch,
    tmp_path,
):
    fake = FakeSession(tmp_path)
    monkeypatch.setattr(chat_module, "_make_session", lambda **_kwargs: fake)

    result = CliRunner().invoke(
        chat,
        ["--output", str(tmp_path), "--message", "Create one problem"],
        terminal_width=180,
    )

    assert result.exit_code == 0
    assert '"role": "user"' in result.output
    assert '"content": "Create one problem"' in result.output
    assert '"role": "assistant"' in result.output
    assert '"content": "I prepared a no-model-call plan."' in result.output


def test_worker_json_is_decoded_once_and_separate_runs_do_not_mix():
    stream = io.StringIO()
    renderer = RichChatRenderer(Console(file=stream, force_terminal=False, width=60))
    first = json.dumps({"vbagent_io": 1, "event": "input", "agent": "DraftA", "input": "Line one\nLine two"}) + "\n"
    second = json.dumps({"vbagent_io": 1, "event": "output", "agent": "DraftB", "output": {"problem_latex": "\\item Question\n\\task Answer"}}) + "\n"
    renderer.worker_output({"run_id": "run-a", "content": first[:45], "offset": 0})
    assert stream.getvalue() == ""
    renderer.worker_output({"run_id": "run-b", "content": second})
    renderer.worker_output({"run_id": "run-a", "content": first[45:]})

    rendered = stream.getvalue()
    assert rendered.count("[INPUT] DraftA") == 1
    assert rendered.count("[OUTPUT] DraftB") == 1
    assert '"lines": [' in rendered
    assert '"Line one",\n' in rendered
    assert '"offset"' not in rendered
    assert '"content": "\\n' not in rendered
    assert "[AGENT I/O]" not in rendered


def test_explicit_logs_uses_structured_renderer_even_without_trace(monkeypatch):
    fake = FakeSession()
    event = {"vbagent_io": 1, "event": "input", "agent": "Draft", "input": "First\nSecond"}
    fake.read_new_worker_io = lambda run_id: {
        "ok": True,
        "data": {"run_id": run_id, "content": json.dumps(event) + "\n", "eof": True},
    }
    monkeypatch.setattr(chat_module, "_make_session", lambda **_kwargs: fake)

    result = CliRunner().invoke(chat, ["--no-trace"], input="/logs example-run\n/exit\n")

    assert result.exit_code == 0
    assert "[INPUT] Draft" in result.output
    assert '"lines": [' in result.output
    assert '"vbagent_io"' not in result.output


def test_chat_interactive_tools_and_exit(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(chat_module, "_make_session", lambda **_kwargs: fake)

    result = CliRunner().invoke(chat, input="/tools\n/clear\n/exit\n")

    assert result.exit_code == 0
    assert "authoring_plan" in result.output
    assert "You:" in result.output
    assert "older submitted messages" in result.output
    assert '"event": "conversation_cleared"' in result.output
    assert "Chat closed" in result.output
    assert fake.cleared is True


def test_chat_opens_and_exits_without_loading_mcp_or_agents(monkeypatch):
    def fail_if_loaded(**_kwargs):
        raise AssertionError("session should remain lazy")

    monkeypatch.setattr(chat_module, "_make_session", fail_if_loaded)
    result = CliRunner().invoke(chat, input="/exit\n")

    assert result.exit_code == 0
    assert "loaded on first message" in result.output
    assert "Chat closed" in result.output


def test_importing_chat_policy_does_not_eagerly_load_mcp_or_agents():
    checked = subprocess.run(
        [sys.executable, "-c", (
            "import sys; import vbagent.cli.interfaces.chat; "
            "assert 'vbagent.mcp.server' not in sys.modules; "
            "assert 'agents' not in sys.modules"
        )], capture_output=True, text=True, check=False,
    )
    assert checked.returncode == 0, checked.stderr


def test_chat_confirm_dispatches_pending_plan_without_second_controller_turn(monkeypatch):
    fake = FakeSession()

    def send_plan(message, *, show_spinner=True):
        fake.messages.append((message, show_spinner))
        fake.pending_run_id = "planned-run"
        return "Plan ready. Type confirm."

    fake.send = send_plan
    monkeypatch.setattr(chat_module, "_make_session", lambda **_kwargs: fake)

    result = CliRunner().invoke(chat, input="Plan one problem\nconfirm\n/exit\n")

    assert result.exit_code == 0
    assert fake.messages == [("Plan one problem", True)]
    assert fake.confirmed_runs == ["planned-run"]
    assert '"action": "start_background_generation"' in result.output
    assert "Start this generation in the background?" in result.output
    assert '"event": "background_generation_started"' in result.output
    assert '"state": "dispatched"' in result.output


def test_chat_explicit_creation_intent_starts_after_plan_without_second_yes(monkeypatch):
    fake = FakeSession()

    def send_plan(message, *, show_spinner=True):
        fake.messages.append((message, show_spinner))
        fake.pending_run_id = "auto-start-run"
        fake.authorized_pending_run_id = "auto-start-run"
        return "Plan ready. The terminal will apply the original creation intent."

    fake.send = send_plan
    monkeypatch.setattr(chat_module, "_make_session", lambda **_kwargs: fake)

    result = CliRunner().invoke(chat, input="Create one kinematics problem\n/exit\n")

    assert result.exit_code == 0
    assert fake.messages == [("Create one kinematics problem", True)]
    assert fake.confirmed_runs == ["auto-start-run"]
    assert '"event": "background_start_authorized"' in result.output
    assert '"authorization_source": "explicit_creation_intent"' in result.output
    assert '"confirmation_required": false' in result.output
    assert '"event": "approval_required"' not in result.output
    assert '"event": "background_generation_started"' in result.output


@pytest.mark.parametrize("answer", ["yes", "yes please", "confirm", "go ahead", "/approve"])
def test_plain_confirmation_approves_staged_tool_not_a_second_plan(monkeypatch, answer):
    fake = FakeSession()

    def stage(message, *, show_spinner=True):
        fake.messages.append((message, show_spinner))
        fake.pending_run_id = "older-plan"
        fake.pending_tool_name = "authoring_start"
        return "Rebuild main.tex and main.pdf?"

    fake.send = stage
    monkeypatch.setattr(chat_module, "_make_session", lambda **_kwargs: fake)
    result = CliRunner().invoke(chat, input=f"Maybe rebuild this\n{answer}\n/exit\n")

    assert result.exit_code == 0
    assert len(fake.messages) == 1
    assert fake.approved_tools == ["authoring_start"]
    assert fake.confirmed_runs == []
    assert "Reply yes or no" in result.output


@pytest.mark.parametrize("answer", ["no", "no thanks", "not yet", "/decline"])
def test_plain_decline_does_not_dispatch_or_reenter_controller(monkeypatch, answer):
    fake = FakeSession()

    def plan(message, *, show_spinner=True):
        fake.messages.append((message, show_spinner))
        fake.pending_run_id = "proposed-run"
        return "Start this generation in the background?"

    fake.send = plan
    monkeypatch.setattr(chat_module, "_make_session", lambda **_kwargs: fake)
    result = CliRunner().invoke(chat, input=f"Plan one problem\n{answer}\n/exit\n")

    assert result.exit_code == 0
    assert len(fake.messages) == 1
    assert fake.confirmed_runs == []
    assert fake.pending_run_id is None
    assert '"event": "approval_declined"' in result.output


def test_rebuild_result_is_not_reported_as_background_generation():
    output = io.StringIO()
    renderer = RichChatRenderer(Console(file=output, width=160))
    chat_module._render_command_result({
        "ok": True,
        "data": {"run_id": "r", "action": "rebuild", "dispatched": False,
                 "status": {"publication": {"compile_success": True, "problem_numbers": [6, 7]}}},
    }, renderer)
    assert '"event": "document_rebuilt"' in output.getvalue()
    assert '"generation_started": false' in output.getvalue()
    assert "background_generation_started" not in output.getvalue()


def test_chat_one_keyboard_interrupt_cancels_request_and_exits_cleanly(monkeypatch):
    fake = FakeSession()

    def interrupt(_message, *, show_spinner=True):
        raise KeyboardInterrupt

    fake.send = interrupt
    monkeypatch.setattr(chat_module, "_make_session", lambda **_kwargs: fake)

    result = CliRunner().invoke(chat, input="Plan one problem\n")

    assert result.exit_code == 0
    assert "Current request cancelled. Chat closed." in result.output
    assert "Aborted" not in result.output


def test_chat_remains_available_as_top_level_command():
    result = CliRunner().invoke(main, ["chat", "--help"])

    assert result.exit_code == 0
    assert "durable authoring workflow" in result.output
