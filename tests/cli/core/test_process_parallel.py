"""Regression tests for image and TeX parallel processing."""

import io
import threading
import time
from types import SimpleNamespace

from click.testing import CliRunner
from rich.console import Console

from vbagent.cli.core import process as process_cli


def _console():
    return Console(file=io.StringIO(), force_terminal=False)


def test_parallel_image_results_return_in_input_order(monkeypatch, tmp_path):
    image_paths = [str(tmp_path / f"problem_{index}.png") for index in range(1, 4)]

    def fake_process_image(image_path, **kwargs):
        # Complete in reverse order to prove collection is not completion-order
        # dependent.
        time.sleep((4 - int(image_path.rsplit("_", 1)[1].split(".")[0])) * 0.01)
        return SimpleNamespace(source_path=image_path, tikz_code=None)

    monkeypatch.setattr(process_cli, "process_image", fake_process_image)
    monkeypatch.setattr(process_cli, "save_pipeline_result_organized", lambda *args: {})

    results, failures = process_cli._process_images_parallel(
        image_paths=image_paths,
        variant_types=[],
        generate_alternate=False,
        generate_ideas=False,
        use_context=True,
        output_dir=str(tmp_path / "output"),
        num_workers=3,
        console=_console(),
        assess_difficulty=False,
        merge_metadata=False,
        use_cache=False,
        solve=False,
        do_compile=False,
        verbose_compile=False,
        verbose=False,
    )

    assert failures == 0
    assert [result.source_path for result in results] == image_paths


def test_tex_items_run_in_parallel_and_keep_original_numbers(monkeypatch, tmp_path):
    tex_path = tmp_path / "problems.tex"
    tex_path.write_text("\\item One\n\\item Two\n\\item Three\n\\item Four\n")

    active = 0
    peak = 0
    lock = threading.Lock()

    def fake_process_tex_item(tex_content, source_path, **kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return SimpleNamespace(
            source_path=source_path,
            latex=tex_content,
            tikz_code=None,
        )

    monkeypatch.setattr(process_cli, "process_tex_item", fake_process_tex_item)

    records, failures = process_cli._process_tex_input(
        str(tex_path),
        (2, 4),
        [],
        False,
        False,
        True,
        False,
        False,
        _console(),
        "3",
    )

    assert failures == 0
    assert [item_number for item_number, _ in records] == [2, 3, 4]
    assert peak >= 2


def test_run_returns_failure_exit_code_for_partial_image_failure(monkeypatch, tmp_path):
    image_path = tmp_path / "problem.png"
    image_path.write_bytes(b"image")

    monkeypatch.setattr(
        process_cli,
        "_process_image_input",
        lambda *args, **kwargs: ([], 1),
    )

    result = CliRunner().invoke(
        process_cli.run,
        ["--input", str(image_path), "--quiet"],
    )

    assert result.exit_code == 1
