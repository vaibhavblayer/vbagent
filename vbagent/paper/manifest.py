"""PaperManifest — persistent state tracking for paper problems."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from .models import PaperState, ProblemEntry


class PaperManifest:
    """Manages manifest.json in the base directory."""

    def __init__(self, base_dir: Path = Path("agentic")):
        self.base_dir = Path(base_dir)
        self._manifest_path = self.base_dir / "manifest.json"

    def exists(self) -> bool:
        return self._manifest_path.exists()

    def load(self) -> PaperState:
        if not self._manifest_path.exists():
            return self._create_default()
        try:
            data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            return PaperState.model_validate(data)
        except Exception:
            return self._create_default()

    def save(self, state: PaperState) -> None:
        state.update_timestamp()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path.write_text(
            state.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )

    def add_problem(self, state: PaperState, entry: ProblemEntry) -> int:
        state.problems.append(entry)
        self.save(state)
        return entry.serial

    def get_next_serial(self, state: PaperState | None = None) -> int:
        """Next serial, considering both manifest and files on disk."""
        max_manifest = 0
        if state and state.problems:
            max_manifest = max(p.serial for p in state.problems)
        max_disk = self._detect_disk_serial()
        return max(max_manifest, max_disk) + 1

    def _detect_disk_serial(self) -> int:
        """Scan scans/ dir for highest Problem_N number."""
        scans_dir = self.base_dir / "scans"
        if not scans_dir.exists():
            return 0
        pattern = re.compile(r"Problem_(\d+)\.tex$", re.IGNORECASE)
        highest = 0
        for f in scans_dir.iterdir():
            m = pattern.match(f.name)
            if m:
                highest = max(highest, int(m.group(1)))
        return highest

    def _create_default(self) -> PaperState:
        return PaperState(
            paper_id=uuid.uuid4().hex[:12],
            subject="physics",
            base_dir=str(self.base_dir),
        )
