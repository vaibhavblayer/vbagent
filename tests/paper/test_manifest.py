"""Tests for PaperManifest — state persistence and serial numbering."""

import json
import pytest
from pathlib import Path

from vbagent.paper.manifest import PaperManifest
from vbagent.paper.models import PaperState, ProblemEntry


class TestPaperManifest:
    def test_create_default_when_no_manifest(self, tmp_path):
        manifest = PaperManifest(base_dir=tmp_path)
        state = manifest.load()
        assert isinstance(state, PaperState)
        assert state.subject == "physics"
        assert state.problems == []
        assert len(state.paper_id) == 12

    def test_exists_false_initially(self, tmp_path):
        manifest = PaperManifest(base_dir=tmp_path)
        assert not manifest.exists()

    def test_save_and_load_round_trip(self, tmp_path):
        manifest = PaperManifest(base_dir=tmp_path)
        state = PaperState(paper_id="test123", subject="chemistry", tone="mechanistic")
        state.problems.append(
            ProblemEntry(serial=1, filename="Problem_1.tex", subject="chemistry", topic="organic")
        )
        manifest.save(state)

        assert manifest.exists()
        loaded = manifest.load()
        assert loaded.paper_id == "test123"
        assert loaded.subject == "chemistry"
        assert loaded.tone == "mechanistic"
        assert len(loaded.problems) == 1
        assert loaded.problems[0].serial == 1

    def test_add_problem(self, tmp_path):
        manifest = PaperManifest(base_dir=tmp_path)
        state = PaperState(paper_id="ap1", subject="physics")
        manifest.save(state)

        entry = ProblemEntry(serial=1, filename="Problem_1.tex", subject="physics", topic="mechanics")
        manifest.add_problem(state, entry)

        loaded = manifest.load()
        assert len(loaded.problems) == 1
        assert loaded.problems[0].topic == "mechanics"

    def test_get_next_serial_empty(self, tmp_path):
        manifest = PaperManifest(base_dir=tmp_path)
        state = PaperState(paper_id="s1", subject="physics")
        assert manifest.get_next_serial(state) == 1

    def test_get_next_serial_from_manifest(self, tmp_path):
        manifest = PaperManifest(base_dir=tmp_path)
        state = PaperState(paper_id="s2", subject="physics")
        state.problems = [
            ProblemEntry(serial=3, filename="Problem_3.tex", subject="physics", topic="optics"),
            ProblemEntry(serial=7, filename="Problem_7.tex", subject="physics", topic="waves"),
        ]
        assert manifest.get_next_serial(state) == 8

    def test_get_next_serial_from_disk(self, tmp_path):
        manifest = PaperManifest(base_dir=tmp_path)
        scans = tmp_path / "scans"
        scans.mkdir()
        (scans / "Problem_5.tex").write_text("\\item Q5")
        (scans / "Problem_12.tex").write_text("\\item Q12")
        (scans / "notes.txt").write_text("not a problem")

        state = PaperState(paper_id="s3", subject="physics")
        assert manifest.get_next_serial(state) == 13

    def test_get_next_serial_disk_beats_manifest(self, tmp_path):
        manifest = PaperManifest(base_dir=tmp_path)
        scans = tmp_path / "scans"
        scans.mkdir()
        (scans / "Problem_20.tex").write_text("\\item Q20")

        state = PaperState(paper_id="s4", subject="physics")
        state.problems = [
            ProblemEntry(serial=5, filename="Problem_5.tex", subject="physics", topic="x"),
        ]
        # Disk has 20, manifest has 5 → next should be 21
        assert manifest.get_next_serial(state) == 21

    def test_corrupt_manifest_creates_fresh(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("not valid json {{{", encoding="utf-8")

        manifest = PaperManifest(base_dir=tmp_path)
        state = manifest.load()
        assert isinstance(state, PaperState)
        assert state.problems == []

    def test_save_creates_directory(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        manifest = PaperManifest(base_dir=nested)
        state = PaperState(paper_id="dir1", subject="physics")
        manifest.save(state)
        assert (nested / "manifest.json").exists()
