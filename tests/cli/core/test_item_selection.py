"""Numbered-problem commands share one selection contract."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

import click
import pytest
from click.testing import CliRunner

from vbagent.cli.compilation.compile_main import compile as compile_command
from vbagent.cli.core.classify import classify
from vbagent.cli.core.process import run
from vbagent.cli.core.scan import scan
from vbagent.cli.generation.animate import animate
from vbagent.cli.generation.generate import generate
from vbagent.cli.generation.solve import solve
from vbagent.cli.item_selection import OPEN_ENDED_ITEM, resolve_item_range
from vbagent.cli.management.archive import product, pyq
from vbagent.cli.management.ref import tikz_group
from vbagent.cli.quality.check import check
from vbagent.pipeline.io import generate_image_paths_from_range


NUMBERED_COMMANDS = (
    run,
    scan,
    classify,
    generate,
    solve,
    animate,
    compile_command,
    check.commands["init"],
    tikz_group.commands["import"],
    pyq,
    product,
)


@pytest.mark.parametrize("command", NUMBERED_COMMANDS, ids=lambda command: command.name)
def test_numbered_commands_expose_the_run_selection_pattern(command):
    options = {parameter.name: parameter for parameter in command.params}

    assert options["from_index"].opts == ["--from"]
    assert options["to_index"].opts == ["--to"]
    assert options["item"].opts == ["--item"]
    for name in ("from_index", "to_index", "item"):
        assert isinstance(options[name].type, click.IntRange)
        assert options[name].type.min == 1


def test_resolve_item_range_uses_inclusive_one_based_contract():
    assert resolve_item_range(None, None, None) is None
    assert resolve_item_range(None, None, 7) == (7, 7)
    assert resolve_item_range(None, 12, None) == (1, 12)
    assert resolve_item_range(5, None, None) == (5, OPEN_ENDED_ITEM)
    assert resolve_item_range(5, 12, None) == (5, 12)


@pytest.mark.parametrize(
    "values, exception",
    [
        ((3, 5, 4), click.UsageError),
        ((5, 3, None), click.UsageError),
        ((0, 3, None), click.BadParameter),
        ((1, 3, 0), click.UsageError),
    ],
)
def test_resolve_item_range_rejects_invalid_combinations(values, exception):
    with pytest.raises(exception):
        resolve_item_range(*values)


def test_open_ended_numbered_image_range_discovers_existing_siblings(tmp_path):
    for number in (2, 4, 10):
        (tmp_path / f"problem_{number:02d}.png").touch()

    selected = generate_image_paths_from_range(
        str(tmp_path / "problem_02.png"),
        (4, OPEN_ENDED_ITEM),
    )

    assert [Path(path).name for path in selected] == [
        "problem_04.png",
        "problem_10.png",
    ]


def test_scan_accepts_run_style_numbered_range_and_uses_batch_outputs(
    monkeypatch, tmp_path
):
    images = tmp_path / "images"
    images.mkdir()
    for number in range(1, 13):
        (images / f"problem_{number}.png").touch()

    calls = []
    scan_module = importlib.import_module("vbagent.cli.core.scan")

    def fake_scan_single(input_path, question_type, subject, output, do_compile,
                         verbose_compile, verbose):
        calls.append((Path(input_path).name, Path(output).name))

    monkeypatch.setattr(scan_module, "_scan_single", fake_scan_single)
    output_dir = tmp_path / "scans"

    result = CliRunner().invoke(
        scan,
        [
            "-i", str(images / "problem_1.png"),
            "--from", "1",
            "--to", "12",
            "--output", str(output_dir),
            "--quiet",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        (f"problem_{number}.png", f"problem_{number}.tex")
        for number in range(1, 13)
    ]


def test_scan_item_keeps_single_file_output_semantics(monkeypatch, tmp_path):
    for number in (1, 5):
        (tmp_path / f"problem_{number}.png").touch()

    calls = []
    scan_module = importlib.import_module("vbagent.cli.core.scan")

    def fake_scan_single_item(input_path, question_type, subject, output,
                              do_compile, verbose_compile, verbose):
        calls.append((Path(input_path).name, output))

    monkeypatch.setattr(
        scan_module,
        "_scan_single",
        fake_scan_single_item,
    )
    output = tmp_path / "selected.tex"

    result = CliRunner().invoke(
        scan,
        [
            "-i", str(tmp_path / "problem_1.png"),
            "--item", "5",
            "--output", str(output),
            "--quiet",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [("problem_5.png", str(output))]


def test_scan_one_item_range_keeps_directory_output_semantics(
    monkeypatch, tmp_path
):
    image = tmp_path / "problem_1.png"
    image.touch()
    calls = []
    scan_module = importlib.import_module("vbagent.cli.core.scan")

    def fake_scan_single(input_path, question_type, subject, output,
                         do_compile, verbose_compile, verbose):
        calls.append((Path(input_path).name, Path(output)))

    monkeypatch.setattr(scan_module, "_scan_single", fake_scan_single)
    output_dir = tmp_path / "scans"

    result = CliRunner().invoke(
        scan,
        [
            "-i", str(image),
            "--from", "1",
            "--to", "1",
            "--output", str(output_dir),
            "--quiet",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [("problem_1.png", output_dir / "problem_1.tex")]


def test_classify_accepts_run_style_numbered_range(monkeypatch, tmp_path):
    for number in range(1, 4):
        (tmp_path / f"problem_{number}.png").touch()

    calls = []

    class FakeClassification:
        subject = "mathematics"
        question_type = "subjective"
        has_diagram = False
        confidence = 0.9
        classified_from = "image"

        def model_dump(self):
            return {"subject": self.subject, "question_type": self.question_type}

        def model_dump_json(self, indent=None):
            return json.dumps(self.model_dump(), indent=indent)

    classifier_module = ModuleType(
        "vbagent.agents.classification.question_classifier"
    )

    def fake_classify(path):
        calls.append(Path(path).name)
        return FakeClassification()

    classifier_module.classify_primary_image = fake_classify
    monkeypatch.setitem(
        sys.modules,
        "vbagent.agents.classification.question_classifier",
        classifier_module,
    )
    output_dir = tmp_path / "classifications"

    result = CliRunner().invoke(
        classify,
        [
            "-i", str(tmp_path / "problem_1.png"),
            "--from", "1",
            "--to", "3",
            "--format", "json",
            "--output", str(output_dir),
            "--quiet",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == ["problem_1.png", "problem_2.png", "problem_3.png"]
    assert sorted(path.name for path in output_dir.glob("*.json")) == [
        "problem_1.json",
        "problem_2.json",
        "problem_3.json",
    ]


def test_compile_item_selects_exactly_one_problem(tmp_path):
    scans = tmp_path / "scans"
    scans.mkdir()
    (scans / "problem_1.tex").write_text(r"\item First.")
    (scans / "problem_2.tex").write_text(r"\item Second.")
    output = tmp_path / "main.tex"

    result = CliRunner().invoke(
        compile_command,
        [
            "--dir", str(scans),
            "--output", str(output),
            "--item", "2",
            "--explicit",
        ],
    )

    assert result.exit_code == 0, result.output
    content = output.read_text()
    assert "problem_2.tex" in content
    assert "problem_1.tex" not in content
