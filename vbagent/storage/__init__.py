"""Storage management for VBAgent.

Provides metadata management and content caching with hash-based deduplication.
"""

from .metadata_manager import MetadataManager
from .content_cache import ContentCache

__all__ = ["MetadataManager", "ContentCache"]
