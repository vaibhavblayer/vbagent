"""Regression tests for generation artifact caching."""

import json
from types import SimpleNamespace

from vbagent.pipeline import generate


def _cache_key(*, with_solution: bool = True, with_diagram: bool = True) -> str:
    return generate._idea_hash(
        ["idea"],
        ["concept"],
        "topic",
        "medium",
        "subjective",
        "physics",
        with_solution,
        with_diagram,
    )


def test_generation_cache_requires_matching_metadata(tmp_path):
    problem_path = tmp_path / "problems" / "problem_1.tex"
    metadata_path = tmp_path / "generation" / "problem_1.json"
    problem_path.parent.mkdir()
    metadata_path.parent.mkdir()
    problem_path.write_text("generated problem")

    assert generate._load_generation_cache(tmp_path, "problem_1", _cache_key()) is None

    metadata_path.write_text(json.dumps({"cache_key": "stale"}))
    assert generate._load_generation_cache(tmp_path, "problem_1", _cache_key()) is None

    metadata_path.write_text(json.dumps({"cache_key": _cache_key()}))
    assert generate._load_generation_cache(tmp_path, "problem_1", _cache_key()) == (
        "generated problem",
        None,
    )


def test_generation_cache_key_includes_optional_outputs():
    full = _cache_key(with_solution=True, with_diagram=True)

    assert _cache_key(with_solution=False, with_diagram=True) != full
    assert _cache_key(with_solution=True, with_diagram=False) != full


def test_saving_generation_removes_stale_tikz(tmp_path, monkeypatch):
    stale_tikz = tmp_path / "tikz" / "problem_1.tex"
    stale_tikz.parent.mkdir()
    stale_tikz.write_text("old diagram")

    monkeypatch.setattr(
        generate,
        "get_config",
        lambda: SimpleNamespace(subject="physics"),
    )
    monkeypatch.setattr(generate, "format_latex", lambda value: value)

    result = generate.GenerationResult(
        base_name="problem_1",
        output_dir=tmp_path,
        problem_tex="new problem",
        tikz_code=None,
        generation_meta={"cache_key": _cache_key(with_diagram=False)},
    )
    generate._save_generation(result)

    assert not stale_tikz.exists()
