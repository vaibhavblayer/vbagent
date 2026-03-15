"""Metadata models for pipeline tracking and caching.

This module provides Pydantic models for tracking pipeline execution,
stage timing, and content caching with hash-based deduplication.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class StageStatus(str, Enum):
    """Status of a pipeline stage."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SourceInfo(BaseModel):
    """Information about the source image."""
    image_path: str = Field(description="Path to source image")
    image_hash: str = Field(description="SHA256 hash of image content")
    file_size: int = Field(description="File size in bytes")


class StageMetadata(BaseModel):
    """Metadata for a single pipeline stage."""
    status: StageStatus = Field(default=StageStatus.PENDING)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None, description="Duration in milliseconds")
    agent_name: Optional[str] = Field(default=None, description="Agent that processed this stage")
    model_name: Optional[str] = Field(default=None, description="LLM model used")
    error_message: Optional[str] = Field(default=None)
    content_hash: Optional[str] = Field(default=None, description="SHA256 hash of output content")
    cache_path: Optional[str] = Field(default=None, description="Path to cached content")
    
    # Stage-specific data
    data: Dict[str, Any] = Field(default_factory=dict, description="Stage-specific metadata")


class ClassificationMetadata(StageMetadata):
    """Metadata for classification stage."""
    subject: Optional[str] = None
    question_type: Optional[str] = None
    has_diagram: Optional[bool] = None
    diagram_type: Optional[str] = None
    difficulty: Optional[str] = None


class PipelineMetadata(BaseModel):
    """Complete metadata for a problem's pipeline execution.
    
    This is the main metadata file stored as .vbagent/metadata/{problem_id}.json
    """
    problem_id: str = Field(description="Unique identifier for this problem")
    source: SourceInfo = Field(description="Source image information")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Pipeline stages
    classification: Optional[ClassificationMetadata] = Field(default=None)
    diagram_analysis: Optional[StageMetadata] = Field(default=None)
    scan: Optional[StageMetadata] = Field(default=None)
    tikz: Optional[StageMetadata] = Field(default=None)
    ideas: Optional[StageMetadata] = Field(default=None)
    alternates: Dict[int, StageMetadata] = Field(default_factory=dict, description="Alternate solutions by index")
    variants: Dict[str, StageMetadata] = Field(default_factory=dict, description="Variants by type")
    
    # Pipeline summary
    total_duration_ms: Optional[int] = Field(default=None)
    stages_completed: int = Field(default=0)
    stages_failed: int = Field(default=0)
    stages_skipped: int = Field(default=0)
    
    # Additional metadata
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration used")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")
    notes: str = Field(default="", description="User notes")
    
    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()
    
    def calculate_summary(self):
        """Calculate pipeline summary statistics."""
        stages = [
            self.classification,
            self.diagram_analysis,
            self.scan,
            self.tikz,
            self.ideas,
        ]
        stages.extend(self.alternates.values())
        stages.extend(self.variants.values())
        
        # Filter out None stages
        stages = [s for s in stages if s is not None]
        
        self.stages_completed = sum(1 for s in stages if s.status == StageStatus.COMPLETED)
        self.stages_failed = sum(1 for s in stages if s.status == StageStatus.FAILED)
        self.stages_skipped = sum(1 for s in stages if s.status == StageStatus.SKIPPED)
        
        # Calculate total duration
        durations = [s.duration_ms for s in stages if s.duration_ms is not None]
        self.total_duration_ms = sum(durations) if durations else None
        
        self.update_timestamp()


class CacheIndex(BaseModel):
    """Index of cached content for fast lookup.
    
    Stored as .vbagent/cache/index.json
    """
    entries: Dict[str, "CacheEntry"] = Field(default_factory=dict, description="Hash -> CacheEntry mapping")
    total_size_bytes: int = Field(default=0)
    last_cleanup: Optional[datetime] = Field(default=None)
    
    def add_entry(self, content_hash: str, entry: "CacheEntry"):
        """Add a cache entry."""
        self.entries[content_hash] = entry
        self.total_size_bytes += entry.size_bytes
    
    def remove_entry(self, content_hash: str):
        """Remove a cache entry."""
        if content_hash in self.entries:
            self.total_size_bytes -= self.entries[content_hash].size_bytes
            del self.entries[content_hash]
    
    def get_size_mb(self) -> float:
        """Get total cache size in MB."""
        return self.total_size_bytes / (1024 * 1024)


class CacheEntry(BaseModel):
    """Entry in the cache index."""
    content_hash: str = Field(description="SHA256 hash of content")
    file_path: str = Field(description="Relative path to cached file")
    content_type: str = Field(description="Type of content (tex, json, tikz)")
    size_bytes: int = Field(description="File size in bytes")
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    access_count: int = Field(default=0, description="Number of times accessed")
    
    # References
    used_by: list[str] = Field(default_factory=list, description="Problem IDs using this content")
    
    def mark_accessed(self):
        """Mark this entry as accessed."""
        self.last_accessed = datetime.now()
        self.access_count += 1



# Legacy models for backward compatibility
class TaxonomyClassification(BaseModel):
    """Taxonomy classification result (placeholder for backward compatibility)."""
    chapter: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None


class EnrichedMetadata(BaseModel):
    """Enriched metadata (placeholder for backward compatibility)."""
    taxonomy: Optional[TaxonomyClassification] = None
    keywords: list[str] = Field(default_factory=list)
