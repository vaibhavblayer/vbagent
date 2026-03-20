#!/usr/bin/env python3
"""Verify Phase 5 completion - check all files exist and are properly structured."""

import sys
from pathlib import Path

def check_file_exists(filepath: str) -> bool:
    """Check if file exists and has content."""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ MISSING: {filepath}")
        return False
    
    if path.stat().st_size == 0:
        print(f"⚠️  EMPTY: {filepath}")
        return False
    
    print(f"✅ EXISTS: {filepath}")
    return True

def check_imports_in_agent(filepath: str, expected_imports: list[str]) -> bool:
    """Check if agent file has all expected imports."""
    path = Path(filepath)
    if not path.exists():
        return False
    
    content = path.read_text()
    missing = []
    
    for imp in expected_imports:
        if imp not in content:
            missing.append(imp)
    
    if missing:
        print(f"⚠️  {filepath} missing imports: {', '.join(missing)}")
        return False
    
    print(f"✅ {filepath} has all imports")
    return True

def main():
    print("=" * 70)
    print("PHASE 5 COMPLETION VERIFICATION")
    print("=" * 70)
    
    all_good = True
    
    # Check new solution prompt files
    print("\n📄 Checking Solution Prompt Files (12 new files)...")
    print("-" * 70)
    
    subjects = ["physics", "chemistry", "mathematics"]
    new_types = ["mcq_mc", "assertion_reason", "match", "passage"]
    
    for subject in subjects:
        print(f"\n{subject.upper()}:")
        for qtype in new_types:
            filepath = f"vbagent/prompts/content_generation/solution/{subject}/{qtype}.py"
            if not check_file_exists(filepath):
                all_good = False
    
    # Check solution agent files have proper imports
    print("\n🔧 Checking Solution Agent Imports (3 files)...")
    print("-" * 70)
    
    expected_imports = [
        "mcq_mc as mcq_mc_prompts",
        "assertion_reason as assertion_reason_prompts",
        "match as match_prompts",
        "passage as passage_prompts",
    ]
    
    for subject in subjects:
        filepath = f"vbagent/agents/content_generation/solution/{subject}.py"
        if not check_imports_in_agent(filepath, expected_imports):
            all_good = False
    
    # Check solution agent files have proper routing
    print("\n🔀 Checking Solution Agent Routing (3 files)...")
    print("-" * 70)
    
    expected_routes = [
        'question_type == "mcq_mc"',
        'question_type == "assertion_reason"',
        'question_type == "match"',
        'question_type == "passage"',
    ]
    
    for subject in subjects:
        filepath = f"vbagent/agents/content_generation/solution/{subject}.py"
        path = Path(filepath)
        if path.exists():
            content = path.read_text()
            missing_routes = [r for r in expected_routes if r not in content]
            if missing_routes:
                print(f"⚠️  {filepath} missing routes: {', '.join(missing_routes)}")
                all_good = False
            else:
                print(f"✅ {filepath} has all routes")
        else:
            all_good = False
    
    # Check orchestrator type mapping
    print("\n🎯 Checking Orchestrator Type Mapping...")
    print("-" * 70)
    
    orchestrator_path = "vbagent/agents/content_generation/solution_orchestrator.py"
    if Path(orchestrator_path).exists():
        content = Path(orchestrator_path).read_text()
        required_mappings = [
            '"match": "match"',
            '"passage": "passage"',
        ]
        missing = [m for m in required_mappings if m not in content]
        if missing:
            print(f"⚠️  Orchestrator missing mappings: {', '.join(missing)}")
            all_good = False
        else:
            print(f"✅ Orchestrator has all type mappings")
    else:
        print(f"❌ Orchestrator file not found")
        all_good = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_good:
        print("✅ PHASE 5 VERIFICATION PASSED")
        print("=" * 70)
        print("\nAll files exist and are properly configured!")
        print("\nQuestion Type Coverage:")
        print("  - Physics: 6 types (subjective, mcq_sc, mcq_mc, assertion_reason, match, passage)")
        print("  - Chemistry: 6 types (subjective, mcq_sc, mcq_mc, assertion_reason, match, passage)")
        print("  - Mathematics: 6 types (subjective, mcq_sc, mcq_mc, assertion_reason, match, passage)")
        print("\nTotal: 18 solution prompts (6 types × 3 subjects)")
        return 0
    else:
        print("❌ PHASE 5 VERIFICATION FAILED")
        print("=" * 70)
        print("\nSome files are missing or improperly configured.")
        print("Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
