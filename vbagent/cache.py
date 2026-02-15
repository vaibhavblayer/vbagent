"""Pipeline cache for incremental processing and resume capability."""

import json
from pathlib import Path
from typing import Optional, Any


class PipelineCache:
    """Manages cached results for pipeline stages."""
    
    CACHE_DIR = ".vbagent/pipeline_cache"
    
    def __init__(self, base_dir: str = "."):
        """Initialize cache.
        
        Args:
            base_dir: Base directory (usually current working directory)
        """
        self.base_dir = Path(base_dir)
        self.cache_root = self.base_dir / self.CACHE_DIR
    
    def _get_problem_dir(self, problem_id: str) -> Path:
        """Get cache directory for a specific problem."""
        return self.cache_root / problem_id
    
    def _ensure_dir(self, path: Path):
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
    
    def has(self, problem_id: str, stage: str) -> bool:
        """Check if cached result exists for a stage.
        
        Args:
            problem_id: Problem identifier (e.g., "problem_1")
            stage: Stage name (classification, scan, tikz, ideas, alternate, variant_numerical)
        
        Returns:
            True if cached result exists
        """
        cache_file = self._get_cache_path(problem_id, stage)
        return cache_file.exists()
    
    def get(self, problem_id: str, stage: str) -> Optional[Any]:
        """Get cached result for a stage.
        
        Args:
            problem_id: Problem identifier
            stage: Stage name
        
        Returns:
            Cached data (dict for JSON, str for text) or None if not found
        """
        cache_file = self._get_cache_path(problem_id, stage)
        if not cache_file.exists():
            return None
        
        try:
            if cache_file.suffix == ".json":
                return json.loads(cache_file.read_text(encoding="utf-8"))
            else:
                return cache_file.read_text(encoding="utf-8")
        except Exception:
            return None
    
    def set(self, problem_id: str, stage: str, data: Any):
        """Save result to cache.
        
        Args:
            problem_id: Problem identifier
            stage: Stage name
            data: Data to cache (dict/list for JSON, str for text)
        """
        cache_file = self._get_cache_path(problem_id, stage)
        self._ensure_dir(cache_file.parent)
        
        try:
            if isinstance(data, (dict, list)):
                cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            else:
                cache_file.write_text(str(data), encoding="utf-8")
        except Exception as e:
            # Silently fail - caching is optional
            pass
    
    def _get_cache_path(self, problem_id: str, stage: str) -> Path:
        """Get cache file path for a stage."""
        problem_dir = self._get_problem_dir(problem_id)
        
        # Map stage names to file paths
        if stage == "classification":
            return problem_dir / "classification.json"
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
            problem_dir = self._get_problem_dir(problem_id)
            if problem_dir.exists():
                import shutil
                shutil.rmtree(problem_dir)
        else:
            if self.cache_root.exists():
                import shutil
                shutil.rmtree(self.cache_root)
    
    def get_cached_stages(self, problem_id: str) -> list[str]:
        """Get list of cached stages for a problem.
        
        Returns:
            List of stage names that have cached results
        """
        problem_dir = self._get_problem_dir(problem_id)
        if not problem_dir.exists():
            return []
        
        stages = []
        if (problem_dir / "classification.json").exists():
            stages.append("classification")
        if (problem_dir / "scan.tex").exists():
            stages.append("scan")
        if (problem_dir / "tikz.tex").exists():
            stages.append("tikz")
        if (problem_dir / "ideas.json").exists():
            stages.append("ideas")
        if (problem_dir / "alternate.tex").exists():
            stages.append("alternate")
        
        variants_dir = problem_dir / "variants"
        if variants_dir.exists():
            for variant_file in variants_dir.glob("*.tex"):
                stages.append(f"variant_{variant_file.stem}")
        
        return stages
