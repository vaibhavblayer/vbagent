"""Integration tests for export tool wrappers."""

import pytest
from pathlib import Path
import tempfile
import shutil

from vbagent.orchestrator.tools import ToolRegistry
from vbagent.orchestrator.tool_wrappers import register_export_tools


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample LaTeX files for testing."""
    files = []
    
    for i in range(3):
        file_path = temp_dir / f"question_{i+1}.tex"
        content = f"\\item Question {i+1}\n"
        file_path.write_text(content)
        files.append(file_path)
    
    return files


@pytest.fixture
def registry():
    """Create a tool registry with export tools registered."""
    reg = ToolRegistry()
    register_export_tools(reg)
    return reg


class TestExportTools:
    """Test cases for export tool wrappers."""
    
    @pytest.mark.asyncio
    async def test_export_files_tool_flat_mode(self, registry, sample_files, temp_dir):
        """Test export_files tool in flat mode."""
        output_dir = temp_dir / "output"
        
        result = await registry.execute(
            "export_files",
            {
                "files": [str(f) for f in sample_files],
                "output": str(output_dir),
                "mode": "flat"
            }
        )
        
        # Verify result structure
        assert "output_dir" in result
        assert "file_count" in result
        assert "mode" in result
        assert result["file_count"] == 3
        assert result["mode"] == "flat"
        
        # Verify files were exported
        assert output_dir.exists()
        exported_files = list(output_dir.glob("*.tex"))
        assert len(exported_files) == 3
    
    @pytest.mark.asyncio
    async def test_export_files_tool_project_mode(self, registry, sample_files, temp_dir):
        """Test export_files tool in project mode."""
        output_dir = temp_dir / "output"
        
        result = await registry.execute(
            "export_files",
            {
                "files": [str(f) for f in sample_files],
                "output": str(output_dir),
                "mode": "project",
                "title": "Test DPP"
            }
        )
        
        # Verify result
        assert result["file_count"] == 3
        assert result["mode"] == "project"
        assert result["main_tex"] is not None
        
        # Verify main.tex exists
        main_tex = Path(result["main_tex"])
        assert main_tex.exists()
        
        # Verify content
        content = main_tex.read_text()
        assert "Test DPP" in content
        assert "\\input{question_001}" in content
    
    @pytest.mark.asyncio
    async def test_export_files_tool_invalid_mode(self, registry, sample_files, temp_dir):
        """Test export_files tool with invalid mode."""
        output_dir = temp_dir / "output"
        
        with pytest.raises(Exception, match="is not one of"):
            await registry.execute(
                "export_files",
                {
                    "files": [str(f) for f in sample_files],
                    "output": str(output_dir),
                    "mode": "invalid"
                }
            )
    
    @pytest.mark.asyncio
    async def test_export_directory_tool(self, registry, sample_files, temp_dir):
        """Test export_directory tool."""
        output_dir = temp_dir / "output"
        
        result = await registry.execute(
            "export_directory",
            {
                "directory": str(temp_dir),
                "output": str(output_dir),
                "mode": "flat",
                "pattern": "*.tex",
                "recursive": False
            }
        )
        
        # Verify result
        assert result["file_count"] == 3
        assert result["mode"] == "flat"
        assert result["source_directory"] == str(temp_dir)
        
        # Verify files were exported
        exported_files = list(output_dir.glob("*.tex"))
        assert len(exported_files) == 3
    
    @pytest.mark.asyncio
    async def test_export_directory_tool_recursive(self, registry, temp_dir):
        """Test export_directory tool with recursive search."""
        # Create nested structure
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        
        (temp_dir / "file1.tex").write_text("File 1")
        (subdir / "file2.tex").write_text("File 2")
        
        output_dir = temp_dir / "output"
        
        result = await registry.execute(
            "export_directory",
            {
                "directory": str(temp_dir),
                "output": str(output_dir),
                "mode": "flat",
                "recursive": True
            }
        )
        
        # Should find both files
        assert result["file_count"] == 2
    
    @pytest.mark.asyncio
    async def test_export_directory_tool_no_files(self, registry, temp_dir):
        """Test export_directory tool when no files match."""
        output_dir = temp_dir / "output"
        
        with pytest.raises(Exception, match="No files matching"):
            await registry.execute(
                "export_directory",
                {
                    "directory": str(temp_dir),
                    "output": str(output_dir),
                    "pattern": "*.pdf"  # No PDF files exist
                }
            )
    
    def test_export_tools_registered(self, registry):
        """Test that export tools are properly registered."""
        tools = registry.list_tools()
        
        assert "export_files" in tools
        assert "export_directory" in tools
    
    def test_export_files_tool_definition(self, registry):
        """Test export_files tool definition."""
        tool = registry.get_tool("export_files")
        
        assert tool is not None
        assert tool.name == "export_files"
        assert "Export LaTeX files" in tool.description
        
        # Verify parameters
        params = tool.parameters
        assert params["type"] == "object"
        assert "files" in params["properties"]
        assert "output" in params["properties"]
        assert "mode" in params["properties"]
        
        # Verify mode enum
        mode_prop = params["properties"]["mode"]
        assert mode_prop["enum"] == ["flat", "structured", "project"]
    
    def test_export_directory_tool_definition(self, registry):
        """Test export_directory tool definition."""
        tool = registry.get_tool("export_directory")
        
        assert tool is not None
        assert tool.name == "export_directory"
        assert "Export all LaTeX files from a directory" in tool.description
        
        # Verify parameters
        params = tool.parameters
        assert "directory" in params["properties"]
        assert "output" in params["properties"]
        assert "pattern" in params["properties"]
        assert "recursive" in params["properties"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
