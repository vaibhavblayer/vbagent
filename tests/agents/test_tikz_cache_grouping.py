"""Tests for stable prompt-cache grouping in iterative TikZ repair."""

from types import SimpleNamespace

from vbagent.agents.diagram import tikz_checker


def test_check_and_fix_reuses_group_across_attempts(monkeypatch):
    group_ids = []
    calls = 0

    credentials = SimpleNamespace(base_url=None)

    def fake_turn(agent, message, **kwargs):
        nonlocal calls
        calls += 1
        group_ids.append(kwargs["cache_group_id"])
        if calls == 1:
            result = SimpleNamespace(
                is_valid=False,
                fixed_tikz_code="fixed once",
                errors_found=[],
            )
        else:
            result = SimpleNamespace(is_valid=True, fixed_tikz_code=None)
        continuation = SimpleNamespace(
            credentials=credentials,
            response_id=f"resp-{calls}",
        )
        return result, continuation

    monkeypatch.setattr(tikz_checker, "_validate_tikz_turn", fake_turn)
    monkeypatch.setattr(tikz_checker, "create_structured_tikz_checker_agent", object)

    success, _, _ = tikz_checker.check_and_fix_tikz(
        r"\begin{tikzpicture}\end{tikzpicture}",
        max_retries=2,
    )

    assert success is True
    assert len(group_ids) == 2
    assert group_ids[0] == group_ids[1]
    assert group_ids[0].startswith("vbagent:tikz-fix:v1:")


def test_different_original_code_uses_different_group(monkeypatch):
    group_ids = []

    def fake_turn(agent, message, **kwargs):
        group_ids.append(kwargs["cache_group_id"])
        result = SimpleNamespace(is_valid=True, fixed_tikz_code=None)
        credentials = SimpleNamespace(base_url=None)
        return result, SimpleNamespace(credentials=credentials, response_id="resp")

    monkeypatch.setattr(tikz_checker, "_validate_tikz_turn", fake_turn)
    monkeypatch.setattr(tikz_checker, "create_structured_tikz_checker_agent", object)

    tikz_checker.check_and_fix_tikz("first", max_retries=0)
    tikz_checker.check_and_fix_tikz("second", max_retries=0)

    assert group_ids[0] != group_ids[1]


def test_followup_turn_uses_previous_response_and_compiler_error(monkeypatch):
    calls = []
    credentials = SimpleNamespace(base_url=None)

    def fake_turn(agent, message, **kwargs):
        calls.append((message, kwargs["previous_response_id"], kwargs["credentials"]))
        if len(calls) == 1:
            error = SimpleNamespace(type="compilation", message="Undefined control sequence")
            result = SimpleNamespace(
                is_valid=False,
                fixed_tikz_code="candidate-v2",
                errors_found=[error],
            )
        else:
            result = SimpleNamespace(is_valid=True, fixed_tikz_code=None)
        return result, SimpleNamespace(
            credentials=credentials,
            response_id=f"resp-{len(calls)}",
        )

    monkeypatch.setattr(tikz_checker, "_validate_tikz_turn", fake_turn)
    monkeypatch.setattr(tikz_checker, "create_structured_tikz_checker_agent", object)

    success, _, _ = tikz_checker.check_and_fix_tikz("candidate-v1")

    assert success is True
    assert calls[0][1:] == (None, None)
    assert calls[1][1] == "resp-1"
    assert calls[1][2] is credentials
    assert "Undefined control sequence" in calls[1][0]
    assert "candidate-v2" in calls[1][0]
