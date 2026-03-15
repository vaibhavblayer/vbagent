"""Content-addressable cache for pipeline outputs.

Stores content by SHA256 hash to enable deduplication.
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple

from vbagent.models.metadata import CacheIndex, CacheEntry


class ContentCache:
    """Content-addressable cache with hash-based deduplication."""
    
    CACHE_DIR = ".vbagent/cache"
    CONTENT_DIR = "content"
    INDEX_FILE = "index.json"
    
    def __init__(self, base_dir: str = "."):
        """Initialize content cache.
        
        Args:
            base_dir: Base directory (usually workspace root)
        """
        self.base_dir = Path(base_dir)
        self.cache_dir = self.base_dir / self.CACHE_DIR
        self.content_dir = self.cache_dir / self.CONTENT_DIR
        self.index_path = self.cache_dir / self.INDEX_FILE
        
        # Create directories
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create index
        self.index = self._load_index()
    
    def _load_index(self) -> CacheIndex:
        """Load cache index from disk."""
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                return CacheIndex.model_validate(data)
            except Exception:
                # Corrupted index, rebuild
                return self._rebuild_index()
        return CacheIndex()
    
    def _save_index(self):
        """Save cache index to disk."""
        self.index_path.write_text(
            self.index.model_dump_json(indent=2),
            encoding="utf-8"
        )
    
    def _rebuild_index(self) -> CacheIndex:
        """Rebuild cache index by scanning content directory."""
        index = CacheIndex()
        
        for file_path in self.content_dir.glob("*"):
            if file_path.is_file():
                content_hash = file_path.stem
                content_type = file_path.suffix.lstrip(".")
                size_bytes = file_path.stat().st_size
                
                entry = CacheEntry(
                    content_hash=content_hash,
                    file_path=str(file_path.relative_to(self.cache_dir)),
                    content_type=content_type,
                    size_bytes=size_bytes,
                )
                index.add_entry(content_hash, entry)
        
        return index
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA256 hash of content.
        
        Args:
            content: String content to hash
            
        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        """Compute SHA256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of SHA256 hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _get_content_path(self, content_hash: str, content_type: str) -> Path:
        """Get path for cached content file."""
        return self.content_dir / f"{content_hash}.{content_type}"
    
    def has(self, content_hash: str) -> bool:
        """Check if content exists in cache.
        
        Args:
            content_hash: SHA256 hash of content
            
        Returns:
            True if content is cached
        """
        return content_hash in self.index.entries
    
    def get(self, content_hash: str, problem_id: Optional[str] = None) -> Optional[str]:
        """Get content from cache.
        
        Args:
            content_hash: SHA256 hash of content
            problem_id: Problem ID accessing this content (for tracking)
            
        Returns:
            Content string or None if not found
        """
        if content_hash not in self.index.entries:
            return None
        
        entry = self.index.entries[content_hash]
        file_path = self.cache_dir / entry.file_path
        
        if not file_path.exists():
            # Cache entry exists but file is missing, remove entry
            self.index.remove_entry(content_hash)
            self._save_index()
            return None
        
        # Update access tracking
        entry.mark_accessed()
        if problem_id and problem_id not in entry.used_by:
            entry.used_by.append(problem_id)
        self._save_index()
        
        return file_path.read_text(encoding="utf-8")
    
    def put(
        self,
        content: str,
        content_type: str,
        problem_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Store content in cache.
        
        Args:
            content: Content to cache
            content_type: Type of content (tex, json, tikz)
            problem_id: Problem ID storing this content
            
        Returns:
            Tuple of (content_hash, cache_path)
        """
        # Compute hash
        content_hash = self.compute_hash(content)
        
        # Check if already cached
        if content_hash in self.index.entries:
            entry = self.index.entries[content_hash]
            # Update usage tracking
            if problem_id and problem_id not in entry.used_by:
                entry.used_by.append(problem_id)
                self._save_index()
            return content_hash, entry.file_path
        
        # Write content to file
        file_path = self._get_content_path(content_hash, content_type)
        file_path.write_text(content, encoding="utf-8")
        
        # Create cache entry
        entry = CacheEntry(
            content_hash=content_hash,
            file_path=str(file_path.relative_to(self.cache_dir)),
            content_type=content_type,
            size_bytes=len(content.encode("utf-8")),
            used_by=[problem_id] if problem_id else [],
        )
        
        # Add to index
        self.index.add_entry(content_hash, entry)
        self._save_index()
        
        return content_hash, entry.file_path
    
    def delete(self, content_hash: str):
        """Delete content from cache.
        
        Args:
            content_hash: SHA256 hash of content to delete
        """
        if content_hash not in self.index.entries:
            return
        
        entry = self.index.entries[content_hash]
        file_path = self.cache_dir / entry.file_path
        
        # Delete file
        if file_path.exists():
            file_path.unlink()
        
        # Remove from index
        self.index.remove_entry(content_hash)
        self._save_index()
    
    def cleanup_unused(self, valid_problem_ids: List[str]):
        """Remove cache entries not used by any valid problem.
        
        Args:
            valid_problem_ids: List of valid problem IDs
        """
        to_delete = []
        
        for content_hash, entry in self.index.entries.items():
            # Check if any of the users are still valid
            has_valid_user = any(pid in valid_problem_ids for pid in entry.used_by)
            if not has_valid_user:
                to_delete.append(content_hash)
        
        for content_hash in to_delete:
            self.delete(content_hash)
        
        self.index.last_cleanup = datetime.now()
        self._save_index()
    
    def cleanup_old(self, days: int = 30):
        """Remove cache entries not accessed in specified days.
        
        Args:
            days: Number of days of inactivity before removal
        """
        cutoff = datetime.now() - timedelta(days=days)
        to_delete = []
        
        for content_hash, entry in self.index.entries.items():
            if entry.last_accessed < cutoff:
                to_delete.append(content_hash)
        
        for content_hash in to_delete:
            self.delete(content_hash)
        
        self.index.last_cleanup = datetime.now()
        self._save_index()
    
    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_entries = len(self.index.entries)
        total_size_mb = self.index.get_size_mb()
        
        by_type = {}
        for entry in self.index.entries.values():
            content_type = entry.content_type
            by_type[content_type] = by_type.get(content_type, 0) + 1
        
        return {
            "total_entries": total_entries,
            "total_size_mb": round(total_size_mb, 2),
            "by_type": by_type,
            "last_cleanup": self.index.last_cleanup,
        }
    
    def clear(self):
        """Clear entire cache."""
        # Delete all content files
        for file_path in self.content_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
        
        # Reset index
        self.index = CacheIndex()
        self._save_index()
