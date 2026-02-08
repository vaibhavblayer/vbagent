"""Export system for flexible LaTeX output formatting.

This module provides the Exporter class for exporting LaTeX files in different formats:
- Flat mode: All files in a single directory
- Structured mode: Organized subdirectories by type
- Project mode: main.tex with \\input{} references
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import shutil


class ExportMode(Enum):
    """Export mode options for different output formats."""
    
    FLAT = "flat"  # All files in one directory
    STRUCTURED = "structured"  # Organized subdirectories
    PROJECT = "project"  # main.tex with \input{} references


@dataclass
class ExportResult:
    """Result of an export operation.
    
    Attributes:
        output_dir: Directory where files were exported
        file_count: Number of files exported
        mode: Export mode used
        main_tex: Path to main.tex file (for PROJECT mode)
        created_at: Timestamp of export operation
    """
    output_dir: Path
    file_count: int
    mode: ExportMode
    main_tex: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary format.
        
        Returns:
            Dictionary representation of export result
        """
        return {
            "output_dir": str(self.output_dir),
            "file_count": self.file_count,
            "mode": self.mode.value,
            "main_tex": str(self.main_tex) if self.main_tex else None,
            "created_at": self.created_at.isoformat()
        }


class Exporter:
    """Handles export of LaTeX files in different formats.
    
    Supports three export modes:
    - Flat: Copy all files to a single directory
    - Structured: Organize files into subdirectories by type
    - Project: Generate main.tex with \\input{} references
    """
    
    # Default LaTeX template for project mode
    DEFAULT_TEMPLATE = r"""\documentclass[12pt,a4paper]{{article}}
\usepackage{{amsmath}}
\usepackage{{amssymb}}
\usepackage{{graphicx}}
\usepackage{{tikz}}
\usepackage{{tasks}}
\usepackage{{geometry}}
\geometry{{margin=1in}}

\title{{{title}}}
\author{{}}
\date{{\today}}

\begin{{document}}

\maketitle

{content}

\end{{document}}
"""
    
    def export(
        self,
        files: list[Path],
        output_dir: Path,
        mode: ExportMode,
        template: Optional[str] = None,
        title: str = "LaTeX Document"
    ) -> ExportResult:
        """Export files in the specified format.
        
        Args:
            files: List of LaTeX file paths to export
            output_dir: Directory where files should be exported
            mode: Export mode (FLAT, STRUCTURED, or PROJECT)
            template: Custom LaTeX template (for PROJECT mode)
            title: Document title (for PROJECT mode)
            
        Returns:
            ExportResult with details of the export operation
            
        Raises:
            ValueError: If files list is empty or mode is invalid
            FileNotFoundError: If any source file doesn't exist
            OSError: If export operation fails (permissions, disk space, etc.)
        """
        # Validate inputs
        if not files:
            raise ValueError("Files list cannot be empty")
        
        # Validate all files exist
        for file_path in files:
            if not file_path.exists():
                raise FileNotFoundError(f"Source file not found: {file_path}")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export based on mode
        if mode == ExportMode.FLAT:
            return self._export_flat(files, output_dir)
        elif mode == ExportMode.STRUCTURED:
            return self._export_structured(files, output_dir)
        elif mode == ExportMode.PROJECT:
            return self._export_project(files, output_dir, template, title)
        else:
            raise ValueError(f"Invalid export mode: {mode}")
    
    def _export_flat(
        self,
        files: list[Path],
        output_dir: Path
    ) -> ExportResult:
        """Export all files to a single directory.
        
        All files are copied to the output directory with their original names.
        If there are name conflicts, files are numbered (file_1.tex, file_2.tex, etc.).
        
        Args:
            files: List of file paths to export
            output_dir: Destination directory
            
        Returns:
            ExportResult with export details
        """
        exported_count = 0
        name_counts = {}  # Track name conflicts
        
        for file_path in files:
            # Handle name conflicts
            base_name = file_path.name
            if base_name in name_counts:
                name_counts[base_name] += 1
                # Add number before extension
                stem = file_path.stem
                suffix = file_path.suffix
                dest_name = f"{stem}_{name_counts[base_name]}{suffix}"
            else:
                name_counts[base_name] = 0
                dest_name = base_name
            
            dest_path = output_dir / dest_name
            shutil.copy2(file_path, dest_path)
            exported_count += 1
        
        return ExportResult(
            output_dir=output_dir,
            file_count=exported_count,
            mode=ExportMode.FLAT
        )
    
    def _export_structured(
        self,
        files: list[Path],
        output_dir: Path
    ) -> ExportResult:
        """Export files organized into subdirectories by type.
        
        Files are organized into subdirectories based on their parent directory name:
        - questions/: Question files
        - solutions/: Solution files
        - diagrams/: Diagram files
        - variants/: Variant files
        - other/: Other files
        
        Args:
            files: List of file paths to export
            output_dir: Destination directory
            
        Returns:
            ExportResult with export details
        """
        exported_count = 0
        
        # Define subdirectory mapping based on common patterns
        subdirs = {
            "questions": ["question", "problems", "exercises"],
            "solutions": ["solution", "answers", "sols"],
            "diagrams": ["diagram", "figures", "images", "tikz"],
            "variants": ["variant", "versions"],
            "scans": ["scan", "scanned"],
        }
        
        for file_path in files:
            # Determine subdirectory based on parent directory name
            parent_name = file_path.parent.name.lower()
            
            # Find matching subdirectory
            target_subdir = "other"  # default
            for subdir, patterns in subdirs.items():
                if any(pattern in parent_name for pattern in patterns):
                    target_subdir = subdir
                    break
            
            # Create subdirectory and copy file
            dest_dir = output_dir / target_subdir
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            dest_path = dest_dir / file_path.name
            
            # Handle name conflicts within subdirectory
            if dest_path.exists():
                counter = 1
                stem = file_path.stem
                suffix = file_path.suffix
                while dest_path.exists():
                    dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            
            shutil.copy2(file_path, dest_path)
            exported_count += 1
        
        return ExportResult(
            output_dir=output_dir,
            file_count=exported_count,
            mode=ExportMode.STRUCTURED
        )
    
    def _export_project(
        self,
        files: list[Path],
        output_dir: Path,
        template: Optional[str],
        title: str
    ) -> ExportResult:
        """Export as a LaTeX project with main.tex and \\input{} references.
        
        Creates a main.tex file that includes all exported files using \\input{}.
        Files are copied to the output directory and referenced by relative paths.
        
        Args:
            files: List of file paths to export
            output_dir: Destination directory
            template: Custom LaTeX template (uses default if None)
            title: Document title
            
        Returns:
            ExportResult with export details including main_tex path
        """
        exported_count = 0
        input_commands = []
        
        # Copy files and build input commands
        for i, file_path in enumerate(files, 1):
            # Create numbered filename for clarity
            dest_name = f"question_{i:03d}.tex"
            dest_path = output_dir / dest_name
            
            shutil.copy2(file_path, dest_path)
            exported_count += 1
            
            # Add input command (without .tex extension as per LaTeX convention)
            input_commands.append(f"\\input{{{dest_name[:-4]}}}")
        
        # Generate main.tex content
        content = "\n\n".join(input_commands)
        
        # Use custom template or default
        if template:
            main_tex_content = template.format(title=title, content=content)
        else:
            main_tex_content = self.DEFAULT_TEMPLATE.format(
                title=title,
                content=content
            )
        
        # Write main.tex
        main_tex_path = output_dir / "main.tex"
        main_tex_path.write_text(main_tex_content)
        
        return ExportResult(
            output_dir=output_dir,
            file_count=exported_count,
            mode=ExportMode.PROJECT,
            main_tex=main_tex_path
        )
    
    def export_with_metadata(
        self,
        files_with_metadata: list[tuple[Path, dict]],
        output_dir: Path,
        mode: ExportMode,
        template: Optional[str] = None,
        title: str = "LaTeX Document"
    ) -> ExportResult:
        """Export files with associated metadata.
        
        Similar to export() but accepts files with metadata dictionaries.
        Metadata can be used for organizing files in structured mode or
        adding comments in project mode.
        
        Args:
            files_with_metadata: List of (file_path, metadata_dict) tuples
            output_dir: Directory where files should be exported
            mode: Export mode (FLAT, STRUCTURED, or PROJECT)
            template: Custom LaTeX template (for PROJECT mode)
            title: Document title (for PROJECT mode)
            
        Returns:
            ExportResult with details of the export operation
        """
        # Extract just the file paths
        files = [f[0] for f in files_with_metadata]
        
        # For now, use standard export
        # Future enhancement: use metadata for better organization
        return self.export(files, output_dir, mode, template, title)
