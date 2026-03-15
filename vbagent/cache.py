"""Pipeline cache for incremental processing and resume capability.

This module provides backward-compatible caching using the new
metadata and content-addressable storage system.
"""

import json
from pathlib import Path
from typing import Optional, Any

from vbagent.storage import MetadataManager, ContentCache
from vbagent.models.metadata import PipelineMetadata, StageStatus


class PipelineCache:
    """Manages cached results for pipeline stages.
    
    This class now uses the new metadata system internally while
    maintaining backward compatibility with the old API.
    """
    
    CACHE_DIR = ".vbagent/pipeline_cache"  # Legacy, not used
    
    def __init__(self, base_dir: str = "."):
        """Initialize cache.
        
        Args:
            base_dir: Base directory (usually current working directory)
        """
        self.base_dir = Path(base_dir)
        self.cache_root = self.base_dir / self.CACHE_DIR  # Legacy
        
        # Use new storage system
        self.metadata_manager = MetadataManager(base_dir)
        self.content_cache = ContentCache(base_dir)
    
    def _get_problem_dir(self, problem_id: str) -> Path:
        """Get cache directory for a specific problem (legacy)."""
        return self.cache_root / problem_id
    
    def _ensure_dir(self, path: Path):
        """Ensure directory exists (legacy)."""
        path.mkdir(parents=True, exist_ok=True)
    
    def has(self, problem_id: str, stage: str) -> bool:
        """Check if cached result exists for a stage.
        
        Args:
            problem_id: Problem identifier (e.g., "problem_1")
            stage: Stage name (classification, scan, tikz, ideas, alternate, variant_numerical)
        
        Returns:
            True if cached result exists
        """
        metadata = self.metadata_manager.load(problem_id)
        if not metadata:
            return False
        
        # Map stage name to metadata field
        if stage == "classification":
            return metadata.classification is not None and metadata.classification.status == StageStatus.COMPLETED
        elif stage == "diagram":
            return metadata.diagram_analysis is not None and metadata.diagram_analysis.status == StageStatus.COMPLETED
        elif stage == "scan":
            return metadata.scan is not None and metadata.scan.status == StageStatus.COMPLETED
        elif stage == "tikz":
            return metadata.tikz is not None and metadata.tikz.status == StageStatus.COMPLETED
        elif stage == "ideas":
            return metadata.ideas is not None and metadata.ideas.status == StageStatus.COMPLETED
        elif stage == "alternate":
            return len(metadata.alternates) > 0
        elif stage.startswith("variant_"):
            variant_type = stage.replace("variant_", "")
            return variant_type in metadata.variants and metadata.variants[variant_type].status == StageStatus.COMPLETED
        
        return False
    
    def get(self, problem_id: str, stage: str) -> Optional[Any]:
        """Get cached result for a stage.
        
        Args:
            problem_id: Problem identifier
            stage: Stage name
        
        Returns:
            Cached data (dict for JSON, str for text) or None if not found
        """
        metadata = self.metadata_manager.load(problem_id)
        if not metadata:
            return None
        
        # Get stage metadata
        stage_meta = None
        if stage == "classification":
            stage_meta = metadata.classification
        elif stage == "diagram":
            stage_meta = metadata.diagram_analysis
        elif stage == "scan":
            stage_meta = metadata.scan
        elif stage == "tikz":
            stage_meta = metadata.tikz
        elif stage == "ideas":
            stage_meta = metadata.ideas
        elif stage == "alternate":
            # Return first alternate if exists
            if metadata.alternates:
                stage_meta = metadata.alternates[0]
        elif stage.startswith("variant_"):
            variant_type = stage.replace("variant_", "")
            stage_meta = metadata.variants.get(variant_type)
        
        if not stage_meta or not stage_meta.content_hash:
            return None
        
        # Get content from cache
        content = self.content_cache.get(stage_meta.content_hash, problem_id)
        
        # Parse JSON if needed
        if stage in ["classification", "diagram", "ideas"]:
            try:
                return json.loads(content) if content else None
            except Exception:
                return None
        
        return content
    
    def set(self, problem_id: str, stage: str, data: Any):
        """Save result to cache.
        
        Args:
            problem_id: Problem identifier
            stage: Stage name
            data: Data to cache (dict/list for JSON, str for text)
        """
        # Load or create metadata
        metadata = self.metadata_manager.load(problem_id)
        if not metadata:
            # Create new metadata (will be populated later)
            from vbagent.models.metadata import SourceInfo
            metadata = PipelineMetadata(
                problem_id=problem_id,
                source=SourceInfo(
                    image_path=f"images/{problem_id}.png",  # Default
                    image_hash="",
                    file_size=0,
                )
            )
        
        # Convert data to string
        if isinstance(data, (dict, list)):
            content = json.dumps(data, indent=2)
            content_type = "json"
        else:
            content = str(data)
            # Determine content type from stage
            if stage == "tikz":
                content_type = "tikz"
            else:
                content_type = "tex"
        
        # Store in content cache
        content_hash, cache_path = self.content_cache.put(content, content_type, problem_id)
        
        # Update metadata
        from vbagent.models.metadata import StageMetadata, ClassificationMetadata
        
        stage_meta = StageMetadata(
            status=StageStatus.COMPLETED,
            content_hash=content_hash,
            cache_path=cache_path,
        )
        
        # Store stage-specific data
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
            metadata.classification = stage_meta
        elif stage == "diagram":
            metadata.diagram_analysis = stage_meta
        elif stage == "scan":
            metadata.scan = stage_meta
        elif stage == "tikz":
            metadata.tikz = stage_meta
        elif stage == "ideas":
            metadata.ideas = stage_meta
        elif stage == "alternate":
            # Add to alternates dict
            idx = len(metadata.alternates)
            metadata.alternates[idx] = stage_meta
        elif stage.startswith("variant_"):
            variant_type = stage.replace("variant_", "")
            metadata.variants[variant_type] = stage_meta
        
        # Save metadata
        self.metadata_manager.save(metadata)
    
    def _get_cache_path(self, problem_id: str, stage: str) -> Path:
        """Get cache file path for a stage (legacy method, not used)."""
        problem_dir = self._get_problem_dir(problem_id)
        
        # Map stage names to file paths
        if stage == "classification":
            return problem_dir / "classification.json"
        elif stage == "diagram":
            return problem_dir / "diagram.json"
        elif stage == "scan":
            return problem_dir / "scan.tex"
        elif stage == "tikz":
            return problem_dir / "tikz.tex"
        elif stage == "ideas":
            return problem_dir / "ideas.json"
        elif stage == "alternate":
            return problem_dir / "alternate.tex"
        elif stage.startswith("variant_"):
            variant_type = stage.replace("variant_", "")
            return problem_dir / "variants" / f"{variant_type}.tex"
        else:
            return problem_dir / f"{stage}.txt"
    
    def clear(self, problem_id: Optional[str] = None):
        """Clear cache.
        
        Args:
            problem_id: If provided, clear only this problem. Otherwise clear all.
        """
        if problem_id:
            # Delete metadata
            self.metadata_manager.delete(problem_id)
            # Content cache cleanup will happen automatically
        else:
            # Clear all metadata
            for pid in self.metadata_manager.list_all():
                self.metadata_manager.delete(pid)
            # Clear content cache
            self.content_cache.clear()
    
    def get_cached_stages(self, problem_id: str) -> list[str]:
        """Get list of cached stages for a problem.
        
        Returns:
            List of stage names that have cached results
        """
        metadata = self.metadata_manager.load(problem_id)
        if not metadata:
            return []
        
        stages = []
        
        if metadata.classification and metadata.classification.status == StageStatus.COMPLETED:
            stages.append("classification")
        if metadata.diagram_analysis and metadata.diagram_analysis.status == StageStatus.COMPLETED:
            stages.append("diagram")
        if metadata.scan and metadata.scan.status == StageStatus.COMPLETED:
            stages.append("scan")
        if metadata.tikz and metadata.tikz.status == StageStatus.COMPLETED:
            stages.append("tikz")
        if metadata.ideas and metadata.ideas.status == StageStatus.COMPLETED:
            stages.append("ideas")
        if metadata.alternates:
            stages.append("alternate")
        
        for variant_type in metadata.variants:
            if metadata.variants[variant_type].status == StageStatus.COMPLETED:
                stages.append(f"variant_{variant_type}")
        
        return stages
