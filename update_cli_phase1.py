#!/usr/bin/env python3
"""
Script to complete Phase 1: CLI Option Standardization

This script updates remaining CLI commands with:
- Standardized options (-i/--input, -o/--output, -v/--verbose)
- Subject-agnostic language
- Multi-subject examples
- Deprecation warnings
"""

import re
from pathlib import Path

# Mapping of old to new option patterns
OPTION_REPLACEMENTS = {
    # Image/tex input standardization
    r'@click\.option\(\s*"-i",\s*"--image",': '@click.option("-i", "--input", "--image",',
    r'@click\.option\(\s*"-t",\s*"--tex",': '@click.option("-i", "--input", "--tex",',
    
    # Help text updates
    r'Path to the physics question image file': 'Input file path (image, tex, or json)',
    r'Path to TeX file': 'Input TeX file path',
    r'physics question': 'question',
    r'Physics question': 'Question',
    r'physics concepts': 'concepts',
    r'physics diagrams': 'diagrams',
}

# Files to update with their specific changes
FILES_TO_UPDATE = {
    'vbagent/cli/main.py': {
        'description': 'VBAgent - Multi-subject question processing pipeline',
        'detail': 'A multi-agent CLI system for processing question images across physics, chemistry, and mathematics.',
    },
    'vbagent/cli/core/process.py': {
        'add_verbose': True,
        'update_examples': True,
    },
    'vbagent/cli/generation/tikz.py': {
        'standardize_input': True,
        'add_subject_examples': True,
    },
    'vbagent/cli/generation/idea.py': {
        'standardize_input': True,
    },
    'vbagent/cli/generation/alternate.py': {
        'standardize_input': True,
    },
    'vbagent/cli/generation/variant.py': {
        'standardize_input': True,
        'rename_type_option': '--variant-type',
    },
    'vbagent/cli/generation/convert.py': {
        'standardize_input': True,
    },
}

def add_deprecation_warning(content: str, old_options: list[str]) -> str:
    """Add deprecation warning code after console initialization."""
    warning_code = "\n    # Show deprecation warnings\n    import sys\n"
    for opt in old_options:
        warning_code += f'    if \'{opt}\' in sys.argv:\n'
        warning_code += f'        console.print("[yellow]Note:[/yellow] {opt} is deprecated, use --input or -i", style="dim")\n'
    
    # Insert after console = _get_console()
    pattern = r'(console = _get_console\(\))'
    replacement = r'\1' + warning_code
    return re.sub(pattern, replacement, content, count=1)

def add_verbose_option(content: str) -> str:
    """Add -v/--verbose option to command."""
    # Find the last @click.option before def
    pattern = r'(@click\.option\([^)]+\)\s*\n)(\s*def\s+\w+)'
    verbose_opt = '''@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output with additional details"
)
'''
    replacement = r'\1' + verbose_opt + r'\2'
    return re.sub(pattern, replacement, content, count=1)

def update_help_text_subjects(content: str) -> str:
    """Add subject examples to help text."""
    examples_addition = '''
    # Chemistry question
    vbagent {command} -i chemistry/thermodynamics.png
    
    # Mathematics problem
    vbagent {command} -i math/calculus.png
'''
    # This would need command-specific logic
    return content

def main():
    print("Phase 1: CLI Option Standardization - Batch Update")
    print("=" * 60)
    
    updated_files = []
    
    for file_path, changes in FILES_TO_UPDATE.items():
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  Skipping {file_path} (not found)")
            continue
        
        print(f"\n📝 Processing {file_path}...")
        content = path.read_text()
        original_content = content
        
        # Apply standard replacements
        for pattern, replacement in OPTION_REPLACEMENTS.items():
            content = re.sub(pattern, replacement, content)
        
        # Apply file-specific changes
        if changes.get('add_verbose'):
            content = add_verbose_option(content)
        
        if changes.get('standardize_input'):
            # Detect which old options are used
            old_opts = []
            if '--image' in content:
                old_opts.append('--image')
            if '--tex' in content and '-t' in content:
                old_opts.append('--tex')
            
            if old_opts:
                content = add_deprecation_warning(content, old_opts)
        
        # Save if changed
        if content != original_content:
            path.write_text(content)
            updated_files.append(file_path)
            print(f"   ✅ Updated")
        else:
            print(f"   ℹ️  No changes needed")
    
    print("\n" + "=" * 60)
    print(f"✅ Updated {len(updated_files)} files")
    print("\nUpdated files:")
    for f in updated_files:
        print(f"  - {f}")
    
    print("\n⚠️  Manual review required for:")
    print("  - Help text examples")
    print("  - Function parameter names")
    print("  - Command-specific logic")
    
    print("\n📋 Next steps:")
    print("  1. Review changes with: git diff")
    print("  2. Test each command: vbagent <command> --help")
    print("  3. Run integration tests")
    print("  4. Update documentation")

if __name__ == "__main__":
    main()
