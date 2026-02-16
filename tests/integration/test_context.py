"""Tests for context store functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vbagent.references.context import (
    ContextStore,
    ContextConfig,
    ReferenceFile,
    CATEGORIES,
    get_context_prompt_section,
)


class TestContextConfig:
    """Tests for ContextConfig."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ContextConfig()
        assert config.enabled is True
        assert config.max_examples_per_category == 5
    
    def test_to_dict(self):
        """Test serialization to dict."""
        config = ContextConfig(enabled=False, max_examples_per_category=3)
        data = config.to_dict()
        assert data["enabled"] is False
        assert data["max_examples_per_category"] == 3
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {"enabled": False, "max_examples_per_category": 10}
        config = ContextConfig.from_dict(data)
        assert config.enabled is False
        assert config.max_examples_per_category == 10


class TestReferenceFile:
    """Tests for ReferenceFile."""
    
    def test_to_dict(self):
        """Test serialization to dict."""
        ref = ReferenceFile(
            name="test.tex",
            category="tikz",
            path="/path/to/test.tex",
            description="Test file",
        )
        data = ref.to_dict()
        assert data["name"] == "test.tex"
        assert data["category"] == "tikz"
        assert data["path"] == "/path/to/test.tex"
        assert data["description"] == "Test file"
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "name": "example.tex",
            "category": "latex",
            "path": "/path/to/example.tex",
            "description": None,
        }
        ref = ReferenceFile.from_dict(data)
        assert ref.name == "example.tex"
        assert ref.category == "latex"


class TestContextStore:
    """Tests for ContextStore."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def store(self, temp_config_dir):
        """Create a ContextStore with temporary directory."""
        ContextStore.reset_instance()
        with patch.object(ContextStore, 'CONFIG_DIR', temp_config_dir):
            store = ContextStore()
            store.config_dir = temp_config_dir
            store.config_path = temp_config_dir / "config.json"
            store.references_path = temp_config_dir / "references.json"
            store.references_dir = temp_config_dir / "references"
            store._ensure_directories()
            yield store
        ContextStore.reset_instance()
    
    def test_directories_created(self, store, temp_config_dir):
        """Test that directories are created."""
        assert store.references_dir.exists()
        for category in CATEGORIES:
            assert (store.references_dir / category).exists()
    
    def test_add_reference(self, store, temp_config_dir):
        """Test adding a reference file."""
        # Create a test file
        test_file = temp_config_dir / "test_tikz.tex"
        test_file.write_text("\\begin{tikzpicture}\n\\end{tikzpicture}")
        
        ref = store.add_reference(
            source_path=str(test_file),
            category="tikz",
            description="Test TikZ file",
        )
        
        assert ref.name == "test_tikz.tex"
        assert ref.category == "tikz"
        assert ref.description == "Test TikZ file"
        assert Path(ref.path).exists()
    
    def test_add_reference_invalid_category(self, store, temp_config_dir):
        """Test adding reference with invalid category."""
        test_file = temp_config_dir / "test.tex"
        test_file.write_text("content")
        
        with pytest.raises(ValueError, match="Invalid category"):
            store.add_reference(str(test_file), "invalid_category")
    
    def test_add_reference_file_not_found(self, store):
        """Test adding non-existent file."""
        with pytest.raises(FileNotFoundError):
            store.add_reference("/nonexistent/file.tex", "tikz")
    
    def test_add_reference_duplicate(self, store, temp_config_dir):
        """Test adding duplicate reference."""
        test_file = temp_config_dir / "test.tex"
        test_file.write_text("content")
        
        store.add_reference(str(test_file), "tikz")
        
        with pytest.raises(FileExistsError):
            store.add_reference(str(test_file), "tikz")
    
    def test_remove_reference(self, store, temp_config_dir):
        """Test removing a reference."""
        test_file = temp_config_dir / "test.tex"
        test_file.write_text("content")
        
        store.add_reference(str(test_file), "tikz")
        assert len(store.list_references("tikz")) == 1
        
        result = store.remove_reference("tikz", "test.tex")
        assert result is True
        assert len(store.list_references("tikz")) == 0
    
    def test_remove_nonexistent_reference(self, store):
        """Test removing non-existent reference."""
        result = store.remove_reference("tikz", "nonexistent.tex")
        assert result is False
    
    def test_list_references(self, store, temp_config_dir):
        """Test listing references."""
        # Add files to different categories
        for i, category in enumerate(["tikz", "latex", "variants"]):
            test_file = temp_config_dir / f"test_{i}.tex"
            test_file.write_text(f"content {i}")
            store.add_reference(str(test_file), category)
        
        # List all
        all_refs = store.list_references()
        assert len(all_refs) == 3
        
        # List by category
        tikz_refs = store.list_references("tikz")
        assert len(tikz_refs) == 1
    
    def test_get_reference_content(self, store, temp_config_dir):
        """Test getting reference content."""
        test_file = temp_config_dir / "test.tex"
        test_file.write_text("\\draw (0,0) -- (1,1);")
        
        store.add_reference(str(test_file), "tikz")
        
        content = store.get_reference_content("tikz", "test.tex")
        assert content == "\\draw (0,0) -- (1,1);"
    
    def test_enable_disable_context(self, store):
        """Test enabling and disabling context."""
        assert store.is_enabled() is True
        
        store.disable_context()
        assert store.is_enabled() is False
        
        store.enable_context()
        assert store.is_enabled() is True
    
    def test_get_context_for_category(self, store, temp_config_dir):
        """Test getting combined context."""
        # Add two files
        for i in range(2):
            test_file = temp_config_dir / f"example_{i}.tex"
            test_file.write_text(f"% Example {i}\n\\draw (0,0);")
            store.add_reference(str(test_file), "tikz", description=f"Example {i}")
        
        context = store.get_context_for_category("tikz")
        assert "Example 0" in context
        assert "Example 1" in context
        assert "\\draw (0,0);" in context
    
    def test_get_context_disabled(self, store, temp_config_dir):
        """Test that context is empty when disabled."""
        test_file = temp_config_dir / "test.tex"
        test_file.write_text("content")
        store.add_reference(str(test_file), "tikz")
        
        store.disable_context()
        context = store.get_context_for_category("tikz")
        assert context == ""
    
    def test_get_stats(self, store, temp_config_dir):
        """Test getting statistics."""
        # Add some files
        for category in ["tikz", "tikz", "latex"]:
            test_file = temp_config_dir / f"test_{category}_{len(store.references)}.tex"
            test_file.write_text("content")
            store.add_reference(str(test_file), category)
        
        stats = store.get_stats()
        assert stats["enabled"] is True
        assert stats["total"] == 3
        assert stats["by_category"]["tikz"] == 2
        assert stats["by_category"]["latex"] == 1
