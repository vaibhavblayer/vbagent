"""Reference store modules for vbagent.

Provides reference context management for agents:
- ReferenceStore: Store and retrieve reference examples for LaTeX/TikZ
- TikZStore: Store and retrieve TikZ diagram examples with metadata
- get_context_prompt_section: Get context for prompts

Usage:
    from vbagent.references import ReferenceStore, TikZStore, get_context_prompt_section
    
    # Use reference store
    store = ReferenceStore.get_instance()
    store.add("example", "content")
    results = store.search("query")
    
    # Use TikZ store
    tikz_store = TikZStore.get_instance()
    context = tikz_store.get_context_for_classification(classification)
    
    # Get context for prompts
    context = get_context_prompt_section("latex")
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import ReferenceStore, SearchResult
    from .tikz_store import TikZReferenceStore, TikZReference, TikZMetadata
    from .context import get_context_prompt_section, set_context_enabled

__all__ = [
    # Reference store
    "ReferenceStore",
    "SearchResult",
    # TikZ store
    "TikZStore",
    "TikZReferenceStore",
    "TikZReference",
    "TikZMetadata",
    # Context utilities
    "get_context_prompt_section",
    "set_context_enabled",
]


def __getattr__(name: str):
    """Lazy import of reference modules."""
    if name in ("ReferenceStore", "SearchResult"):
        from . import store
        return getattr(store, name)
    
    if name in ("TikZStore", "TikZReferenceStore", "TikZReference", "TikZMetadata"):
        from . import tikz_store
        if name == "TikZStore":
            return tikz_store.TikZReferenceStore
        return getattr(tikz_store, name)
    
    if name in ("get_context_prompt_section", "set_context_enabled"):
        from . import context
        return getattr(context, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
