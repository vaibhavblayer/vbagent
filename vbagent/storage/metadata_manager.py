"""Metadata manager for pipeline execution tracking.

Manages metadata files in .vbagent/metadata/ directory.
"""

import json
from pathlib import Path
from typing import Optional, List

from vbagent.models.metadata import PipelineMetadata, StageMetadata, ClassificationMetadata


class MetadataManager:
    """Manages pipeline metadata storage and retrieval."""
    
    METADATA_DIR = ".vbagent/metadata"
    
    def __init__(self, base_dir: str = "."):
        """Initialize metadata manager.
        
        Args:
            base_dir: Base directory (usually workspace root)
        """
        self.base_dir = Path(base_dir)
        self.metadata_dir = self.base_dir / self.METADATA_DIR
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_metadata_path(self, problem_id: str) -> Path:
        """Get path to metadata file for a problem."""
        return self.metadata_dir / f"{problem_id}.json"
    
    def exists(self, problem_id: str) -> bool:
        """Check if metadata exists for a problem."""
        return self._get_metadata_path(problem_id).exists()
    
    def load(self, problem_id: str) -> Optional[PipelineMetadata]:
        """Load metadata for a problem.
        
        Args:
            problem_id: Problem identifier
            
        Returns:
            PipelineMetadata or None if not found
        """
        path = self._get_metadata_path(problem_id)
        if not path.exists():
            return None
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return PipelineMetadata.model_validate(data)
        except Exception as e:
            print(f"Warning: Failed to load metadata for {problem_id}: {e}")
            return None
    
    def save(self, metadata: PipelineMetadata):
        """Save metadata for a problem.
        
        Args:
            metadata: PipelineMetadata to save
        """
        metadata.update_timestamp()
        metadata.calculate_summary()
        
        path = self._get_metadata_path(metadata.problem_id)
        path.write_text(
            metadata.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8"
        )
    
    def delete(self, problem_id: str):
        """Delete metadata for a problem.
        
        Args:
            problem_id: Problem identifier
        """
        path = self._get_metadata_path(problem_id)
        if path.exists():
            path.unlink()
    
    def list_all(self) -> List[str]:
        """List all problem IDs with metadata.
        
        Returns:
            List of problem IDs
        """
        return [p.stem for p in self.metadata_dir.glob("*.json")]
    
    def list_by_subject(self, subject: str) -> List[str]:
        """List problem IDs for a specific subject.
        
        Args:
            subject: Subject name (physics, chemistry, mathematics)
            
        Returns:
            List of problem IDs
        """
        results = []
        for problem_id in self.list_all():
            metadata = self.load(problem_id)
            if metadata and metadata.classification:
                if metadata.classification.subject == subject:
                    results.append(problem_id)
        return results
    
    def list_by_type(self, question_type: str) -> List[str]:
        """List problem IDs for a specific question type.
        
        Args:
            question_type: Question type (mcq_sc, subjective, etc.)
            
        Returns:
            List of problem IDs
        """
        results = []
        for problem_id in self.list_all():
            metadata = self.load(problem_id)
            if metadata and metadata.classification:
                if metadata.classification.question_type == question_type:
                    results.append(problem_id)
        return results
    
    def get_stats(self) -> dict:
        """Get statistics across all metadata.
        
        Returns:
            Dictionary with statistics
        """
        all_ids = self.list_all()
        total = len(all_ids)
        
        if total == 0:
            return {
                "total": 0,
                "by_subject": {},
                "by_type": {},
                "completed": 0,
                "failed": 0,
            }
        
        by_subject = {}
        by_type = {}
        completed = 0
        failed = 0
        
        for problem_id in all_ids:
            metadata = self.load(problem_id)
            if not metadata:
                continue
            
            # Count by subject
            if metadata.classification and metadata.classification.subject:
                subject = metadata.classification.subject
                by_subject[subject] = by_subject.get(subject, 0) + 1
            
            # Count by type
            if metadata.classification and metadata.classification.question_type:
                qtype = metadata.classification.question_type
                by_type[qtype] = by_type.get(qtype, 0) + 1
            
            # Count completion status
            if metadata.stages_failed > 0:
                failed += 1
            elif metadata.stages_completed > 0:
                completed += 1
        
        return {
            "total": total,
            "by_subject": by_subject,
            "by_type": by_type,
            "completed": completed,
            "failed": failed,
        }
    
    def cleanup_orphaned(self, valid_problem_ids: List[str]):
        """Remove metadata for problems not in the valid list.
        
        Args:
            valid_problem_ids: List of valid problem IDs to keep
        """
        all_ids = self.list_all()
        for problem_id in all_ids:
            if problem_id not in valid_problem_ids:
                self.delete(problem_id)
