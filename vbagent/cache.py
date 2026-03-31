"""Pipeline cache for incremental processing and resume capability.

Facade over MetadataManager + ContentCache that maps stage names
to metadata fields and handles serialization.
"""

import json
from typing import Optional, Any

from vbagent.storage import MetadataManager, ContentCache
from vbagent.models.metadata import PipelineMetadata, StageMetadata, StageStatus

# Stages whose cached content is JSON (not raw TeX)
_JSON_STAGES = frozenset({"classification", "diagram", "ideas"})

# Simple stage name → PipelineMetadata attribute name
_STAGE_ATTR = {
    "classification": "classification",
    "diagram": "diagram_analysis",
    "scan": "scan",
    "solution": "solution",
    "tikz": "tikz",
    "options": "options",
    "ideas": "ideas",
    "idea_latex": "idea_latex",
}


class PipelineCache:
    """Manages cached results for pipeline stages.

    Maps stage names (classification, scan, tikz, etc.) to the underlying
    MetadataManager + ContentCache storage layer.
    """

    def __init__(self, base_dir: str = "."):
        self.metadata_manager = MetadataManager(base_dir)
        self.content_cache = ContentCache(base_dir)

    # ------------------------------------------------------------------
    # Internal: single place that maps stage name → StageMetadata
    # ------------------------------------------------------------------

    @staticmethod
    def _get_stage_meta(
        metadata: PipelineMetadata, stage: str
    ) -> Optional[StageMetadata]:
        """Resolve a stage name to its StageMetadata on *metadata*."""
        if stage in _STAGE_ATTR:
            return getattr(metadata, _STAGE_ATTR[stage])
        if stage == "alternate":
            return metadata.alternates.get(0) if metadata.alternates else None
        if stage.startswith("variant_"):
            return metadata.variants.get(stage.removeprefix("variant_"))
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has(self, problem_id: str, stage: str) -> bool:
        """Check if a completed cached result exists for *stage*."""
        metadata = self.metadata_manager.load(problem_id)
        if not metadata:
            return False
        stage_meta = self._get_stage_meta(metadata, stage)
        if stage_meta is None:
            return False
        return stage_meta.status == StageStatus.COMPLETED

    def get(self, problem_id: str, stage: str) -> Optional[Any]:
        """Get cached result for *stage*.

        Returns dict for JSON stages, str for TeX stages, or None.
        """
        metadata = self.metadata_manager.load(problem_id)
        if not metadata:
            return None

        stage_meta = self._get_stage_meta(metadata, stage)
        if not stage_meta or not stage_meta.content_hash:
            return None

        content = self.content_cache.get(stage_meta.content_hash, problem_id)
        if stage in _JSON_STAGES:
            try:
                return json.loads(content) if content else None
            except Exception:
                return None
        return content

    def set(self, problem_id: str, stage: str, data: Any):
        """Save *data* to cache for *stage*."""
        metadata = self.metadata_manager.load(problem_id)
        if not metadata:
            from vbagent.models.metadata import SourceInfo
            metadata = PipelineMetadata(
                problem_id=problem_id,
                source=SourceInfo(
                    image_path=f"images/{problem_id}.png",
                    image_hash="",
                    file_size=0,
                ),
            )

        # Serialize
        if isinstance(data, (dict, list)):
            content = json.dumps(data, indent=2)
            content_type = "json"
        else:
            content = str(data)
            content_type = "tikz" if stage == "tikz" else "tex"

        content_hash, cache_path = self.content_cache.put(
            content, content_type, problem_id
        )

        # Build stage metadata
        from vbagent.models.metadata import ClassificationMetadata

        if stage == "classification" and isinstance(data, dict):
            stage_meta = ClassificationMetadata(
                status=StageStatus.COMPLETED,
                content_hash=content_hash,
                cache_path=cache_path,
                subject=data.get("subject"),
                question_type=data.get("question_type"),
                has_diagram=data.get("has_diagram"),
                diagram_type=data.get("diagram_type"),
            )
        else:
            stage_meta = StageMetadata(
                status=StageStatus.COMPLETED,
                content_hash=content_hash,
                cache_path=cache_path,
            )

        # Assign to the right field
        if stage in _STAGE_ATTR:
            setattr(metadata, _STAGE_ATTR[stage], stage_meta)
        elif stage == "alternate":
            metadata.alternates[len(metadata.alternates)] = stage_meta
        elif stage.startswith("variant_"):
            metadata.variants[stage.removeprefix("variant_")] = stage_meta

        self.metadata_manager.save(metadata)

    def clear(self, problem_id: Optional[str] = None):
        """Clear cache for one problem or everything."""
        if problem_id:
            self.metadata_manager.delete(problem_id)
        else:
            for pid in self.metadata_manager.list_all():
                self.metadata_manager.delete(pid)
            self.content_cache.clear()

    def get_cached_stages(self, problem_id: str) -> list[str]:
        """Return list of completed stage names for *problem_id*."""
        metadata = self.metadata_manager.load(problem_id)
        if not metadata:
            return []

        stages = [
            name
            for name in _STAGE_ATTR
            if (m := getattr(metadata, _STAGE_ATTR[name]))
            and m.status == StageStatus.COMPLETED
        ]
        if metadata.alternates:
            stages.append("alternate")
        for vtype, vmeta in metadata.variants.items():
            if vmeta.status == StageStatus.COMPLETED:
                stages.append(f"variant_{vtype}")
        return stages
