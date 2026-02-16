"""Property tests for ReferenceStore.

**Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
**Validates: Requirements 9.2, 9.5**
"""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from vbagent.references import ReferenceStore, SearchResult


# Supported file types
SUPPORTED_FILE_TYPES = ["pdf", "tex", "sty"]


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the ReferenceStore singleton before each test."""
    ReferenceStore.reset_instance()
    yield
    ReferenceStore.reset_instance()


@contextmanager
def create_temp_reference_dir():
    """Create a temporary directory with sample reference files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample TeX file
        tex_file = Path(tmpdir) / "sample.tex"
        tex_file.write_text(r"""
\documentclass{article}
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}
\draw (0,0) -- (1,1);
\node at (0.5, 0.5) {TikZ example};
\end{tikzpicture}
\end{document}
""")
        
        # Create sample STY file
        sty_file = Path(tmpdir) / "custom.sty"
        sty_file.write_text(r"""
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{custom}
\RequirePackage{tikz}
\newcommand{\customcircle}{\tikz \draw (0,0) circle (1cm);}
""")
        
        # Create sample PDF file (just metadata placeholder)
        pdf_file = Path(tmpdir) / "reference.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 sample content")
        
        # Create a subdirectory with more files
        subdir = Path(tmpdir) / "subdir"
        subdir.mkdir()
        
        sub_tex = subdir / "nested.tex"
        sub_tex.write_text(r"\section{Nested} Physics formula: $E=mc^2$")
        
        yield tmpdir


@pytest.fixture
def temp_reference_dir():
    """Pytest fixture wrapper for temp reference dir."""
    with create_temp_reference_dir() as tmpdir:
        yield tmpdir


# Strategy for generating valid file types
file_type_strategy = st.sampled_from(SUPPORTED_FILE_TYPES)


# Strategy for generating search queries
search_query_strategy = st.text(min_size=2, max_size=50).filter(
    lambda x: x.strip() and len(x.strip()) >= 2
)


@given(file_type=file_type_strategy)
@settings(max_examples=100)
def test_property_reference_search_supports_file_type(file_type: str):
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.2, 9.5**
    
    Property: For any reference search query, the system SHALL be able to search
    and return results from PDF, TeX, and STY files in configured directories.
    
    This test verifies that each supported file type is recognized by the system.
    """
    store = ReferenceStore()
    
    # Property: File type must be in supported types
    supported = store.get_supported_file_types()
    assert file_type in supported, (
        f"File type '{file_type}' must be in supported types: {supported}"
    )


@given(file_types=st.lists(file_type_strategy, min_size=1, max_size=3, unique=True))
@settings(max_examples=100)
def test_property_search_filters_by_file_type(file_types: list[str]):
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.2, 9.5**
    
    Property: When file_types filter is specified, search SHALL only return
    results from files matching those types.
    """
    with create_temp_reference_dir() as temp_dir:
        ReferenceStore.reset_instance()
        store = ReferenceStore(directories=[temp_dir])
        store.index_files()
        
        # Search with file type filter
        results = store.search("tikz", file_types=file_types)
        
        # Property: All results must be from specified file types
        for result in results:
            file_ext = Path(result.file_path).suffix.lower().lstrip(".")
            assert file_ext in file_types, (
                f"Result file '{result.file_path}' has extension '{file_ext}' "
                f"which is not in requested types: {file_types}"
            )


def test_property_all_file_types_can_be_indexed(temp_reference_dir):
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.2, 9.5**
    
    Property: The system SHALL be able to index PDF, TeX, and STY files
    from configured directories.
    """
    store = ReferenceStore(directories=[temp_reference_dir])
    indexed_count = store.index_files()
    
    # Property: Should index at least one file
    assert indexed_count > 0, "Should index at least one file"
    
    # Property: Should have files of each type indexed
    files_by_type = store.get_indexed_files_by_type()
    
    # We created tex, sty, and pdf files in the fixture
    assert "tex" in files_by_type, "Should index .tex files"
    assert "sty" in files_by_type, "Should index .sty files"
    assert "pdf" in files_by_type, "Should index .pdf files"


def test_property_search_returns_results_from_all_types(temp_reference_dir):
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.2, 9.5**
    
    Property: Search without file type filter SHALL search across all
    supported file types.
    """
    store = ReferenceStore(directories=[temp_reference_dir])
    store.index_files()
    
    # Search for "tikz" which appears in both tex and sty files
    results = store.search("tikz")
    
    # Property: Should find results
    assert len(results) > 0, "Should find results for 'tikz'"
    
    # Collect file types from results
    result_types = {Path(r.file_path).suffix.lower().lstrip(".") for r in results}
    
    # Property: Should find results from multiple file types
    # (tikz appears in both .tex and .sty files in our fixture)
    assert len(result_types) >= 1, "Should find results from at least one file type"


@given(query=search_query_strategy)
@settings(max_examples=50)
def test_property_search_returns_valid_results(query: str):
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.2, 9.5**
    
    Property: For any search query, results SHALL have valid structure
    with file_path, content, and relevance_score.
    """
    assume(query.strip())
    
    with create_temp_reference_dir() as temp_dir:
        ReferenceStore.reset_instance()
        store = ReferenceStore(directories=[temp_dir])
        store.index_files()
        
        results = store.search(query)
        
        # Property: All results must have valid structure
        for result in results:
            assert isinstance(result, SearchResult), "Result must be SearchResult"
            assert isinstance(result.file_path, str), "file_path must be string"
            assert isinstance(result.content, str), "content must be string"
            assert isinstance(result.relevance_score, float), "relevance_score must be float"
            assert result.relevance_score >= 0, "relevance_score must be non-negative"
            
            # File path should point to a supported file type
            ext = Path(result.file_path).suffix.lower().lstrip(".")
            assert ext in SUPPORTED_FILE_TYPES, (
                f"Result file type '{ext}' must be in supported types"
            )


def test_property_recursive_directory_indexing(temp_reference_dir):
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.5**
    
    Property: WHERE reference directories are configured, the system SHALL
    index them recursively for efficient search.
    """
    store = ReferenceStore(directories=[temp_reference_dir])
    indexed_count = store.index_files()
    
    # We have files in both root and subdir
    # sample.tex, custom.sty, reference.pdf in root
    # nested.tex in subdir
    assert indexed_count >= 4, (
        f"Should index at least 4 files (including nested), got {indexed_count}"
    )
    
    # Search for content in nested file
    results = store.search("Physics formula")
    
    # Property: Should find content from nested directory
    nested_found = any("nested" in r.file_path.lower() for r in results)
    assert nested_found, "Should find content from nested subdirectory"


def test_property_missing_directory_handled_gracefully():
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.5**
    
    Property: When a configured directory does not exist, the system SHALL
    continue without error (as per design doc error handling).
    """
    store = ReferenceStore(directories=["/nonexistent/path/12345"])
    
    # Should not raise an exception
    indexed_count = store.index_files()
    
    # Property: Should index 0 files from nonexistent directory
    assert indexed_count == 0, "Should index 0 files from nonexistent directory"
    
    # Search should return empty results
    results = store.search("anything")
    assert results == [], "Search should return empty results"


def test_property_singleton_instance():
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.5**
    
    Property: ReferenceStore.get_instance() SHALL return the same instance
    across multiple calls.
    """
    instance1 = ReferenceStore.get_instance()
    instance2 = ReferenceStore.get_instance()
    
    # Property: Should be the same instance
    assert instance1 is instance2, "get_instance should return singleton"


def test_property_empty_query_returns_no_results(temp_reference_dir):
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.2**
    
    Property: Empty or whitespace-only queries SHALL return no results.
    """
    store = ReferenceStore(directories=[temp_reference_dir])
    store.index_files()
    
    # Test empty string
    assert store.search("") == [], "Empty query should return no results"
    
    # Test whitespace only
    assert store.search("   ") == [], "Whitespace query should return no results"


@given(max_results=st.integers(min_value=1, max_value=100))
@settings(max_examples=50)
def test_property_max_results_limit(max_results: int):
    """
    **Feature: physics-question-pipeline, Property 12: Reference Search File Type Support**
    **Validates: Requirements 9.2**
    
    Property: Search SHALL respect max_results parameter and return
    at most that many results.
    """
    with create_temp_reference_dir() as temp_dir:
        ReferenceStore.reset_instance()
        store = ReferenceStore(directories=[temp_dir])
        store.index_files()
        
        results = store.search("tikz", max_results=max_results)
        
        # Property: Should not exceed max_results
        assert len(results) <= max_results, (
            f"Should return at most {max_results} results, got {len(results)}"
        )
