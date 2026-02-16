#!/usr/bin/env python3
"""Test script to verify Stage 1 classifier fixes."""

import json

print("Testing Stage 1 Structural Classifier")
print("=" * 60)

# Test 1: Import check
print("\n1. Testing imports...")
try:
    from vbagent import classify_structural, StructuralClassification
    print("   ✓ Imports successful")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    exit(1)

# Test 2: Model structure
print("\n2. Testing StructuralClassification model...")
try:
    from pydantic import ValidationError
    
    # Valid data
    data = {
        "question_type": "mcq_sc",
        "has_diagram": False,
        "diagram_type": "none",
        "num_options": 4,
        "num_subquestions": 1,
        "requires_calculus": False,
        "key_concepts": ["friction", "forces"],
        "confidence": 0.95
    }
    result = StructuralClassification(**data)
    print(f"   ✓ Model validation works")
    print(f"   ✓ Fields: {', '.join(result.model_fields.keys())}")
    
    # Check no chapter/topic/difficulty
    assert "chapter" not in result.model_fields
    assert "topic" not in result.model_fields
    assert "difficulty" not in result.model_fields
    print(f"   ✓ No chapter/topic/difficulty fields (correct!)")
    
except Exception as e:
    print(f"   ✗ Model test failed: {e}")
    exit(1)

# Test 3: Config check
print("\n3. Testing configuration...")
try:
    from vbagent.config import get_config
    config = get_config()
    print(f"   ✓ Classifier model: {config.classifier.model}")
    print(f"   ✓ Classifier reasoning: {config.classifier.reasoning_effort}")
    print(f"   ✓ Confidence threshold: {config.classifier_confidence_threshold}")
    
    # Check nano is configured
    assert config.classifier.model == "gpt-5-nano"
    print(f"   ✓ Using gpt-5-nano (correct!)")
    
except Exception as e:
    print(f"   ✗ Config test failed: {e}")
    exit(1)

# Test 4: Reasoning display fix
print("\n4. Testing reasoning display...")
try:
    from vbagent.config import REASONING_SUPPORT
    nano_support = REASONING_SUPPORT.get("gpt-5-nano")
    print(f"   ✓ gpt-5-nano reasoning support: {nano_support}")
    assert nano_support is None
    print(f"   ✓ Correctly shows None (no reasoning support)")
    
except Exception as e:
    print(f"   ✗ Reasoning test failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("All tests passed! ✓")
print("\nTo test with actual image:")
print("  from vbagent import classify_structural")
print("  result = classify_structural('image.png')")
print("  print(result.model_dump_json(indent=2))")
