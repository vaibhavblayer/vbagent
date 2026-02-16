"""Test import performance with lazy loading."""

import timeit
import sys


def test_package_import_is_fast():
    """Verify that importing vbagent package is fast (no heavy deps loaded)."""
    # Clear any cached imports
    modules_to_clear = [k for k in sys.modules if k.startswith('vbagent')]
    for mod in modules_to_clear:
        del sys.modules[mod]
    
    # Time the import
    import_time = timeit.timeit(
        "import vbagent",
        setup="import sys; [sys.modules.pop(k, None) for k in list(sys.modules) if k.startswith('vbagent')]",
        number=1,
    )
    
    print(f"vbagent import time: {import_time:.4f}s")
    
    # Should be under 0.5s without heavy deps
    assert import_time < 0.5, f"Import too slow: {import_time:.4f}s"


def test_agents_module_import_is_fast():
    """Verify that importing vbagent.agents is fast."""
    import_time = timeit.timeit(
        "from vbagent import agents",
        setup="import sys; [sys.modules.pop(k, None) for k in list(sys.modules) if k.startswith('vbagent')]",
        number=1,
    )
    
    print(f"vbagent.agents import time: {import_time:.4f}s")
    assert import_time < 0.5, f"Import too slow: {import_time:.4f}s"


def test_heavy_deps_not_loaded_on_import():
    """Verify heavy dependencies aren't loaded until needed."""
    # Clear modules
    modules_to_clear = [k for k in sys.modules if k.startswith(('vbagent', 'openai', 'agents', 'pydantic'))]
    for mod in modules_to_clear:
        sys.modules.pop(mod, None)
    
    import vbagent
    
    # These should NOT be loaded yet
    assert 'openai' not in sys.modules, "openai loaded prematurely"
    assert 'agents' not in sys.modules, "agents SDK loaded prematurely"
    
    print("Heavy deps correctly deferred")


def test_classify_triggers_import():
    """Verify accessing classify loads the necessary modules."""
    import subprocess
    
    # Run in subprocess to get clean module state
    result = subprocess.run(
        [sys.executable, "-c", """
import sys
import vbagent

# Access classify - this should trigger lazy import
_ = vbagent.classify

# Check modules loaded
assert 'vbagent.agents' in sys.modules, "agents not loaded"
assert 'vbagent.agents.classifier' in sys.modules, "classifier not loaded"
print("OK")
"""],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed: {result.stderr}"
    print("Lazy import triggers correctly")


def benchmark_imports():
    """Run detailed benchmark of import times."""
    import subprocess
    
    benchmarks = [
        ("import vbagent", "Package import (lazy)"),
        ("from vbagent import agents", "Agents module (lazy)"),
        ("from vbagent.models import ClassificationResult", "Models import"),
        ("from vbagent.config import get_config", "Config import"),
        ("import vbagent; _ = vbagent.classify", "Trigger classify (heavy)"),
        ("import vbagent; _ = vbagent.scan", "Trigger scan (heavy)"),
        ("import vbagent; _ = vbagent.generate_tikz", "Trigger tikz (heavy)"),
    ]
    
    for code, label in benchmarks:
        result = subprocess.run(
            [sys.executable, "-c", f"import timeit; t = timeit.timeit({code!r}, number=1); print(f'{{t:.4f}}')"],
            capture_output=True,
            text=True,
        )
        time_str = result.stdout.strip() if result.returncode == 0 else "ERROR"
        print(f"{label:40} {time_str}s")


if __name__ == "__main__":
    print("=== Import Performance Tests ===\n")
    
    test_package_import_is_fast()
    test_agents_module_import_is_fast()
    test_heavy_deps_not_loaded_on_import()
    test_classify_triggers_import()
    
    print("\n=== Benchmarks ===\n")
    benchmark_imports()
    
    print("\n✓ All tests passed!")
