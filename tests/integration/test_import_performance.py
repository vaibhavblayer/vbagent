"""Test import performance with lazy loading.

All tests that clear sys.modules run in subprocesses to avoid
corrupting module state for other tests in the suite.
"""

import subprocess
import sys


def test_package_import_is_fast():
    """Verify that importing vbagent package is fast (no heavy deps loaded)."""
    result = subprocess.run(
        [sys.executable, "-c", """
import timeit
import sys

# Clear any cached imports
[sys.modules.pop(k, None) for k in list(sys.modules) if k.startswith('vbagent')]

import_time = timeit.timeit(
    "import vbagent",
    setup="import sys; [sys.modules.pop(k, None) for k in list(sys.modules) if k.startswith('vbagent')]",
    number=1,
)

print(f"{import_time:.4f}")
assert import_time < 0.5, f"Import too slow: {import_time:.4f}s"
"""],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed: {result.stderr}"
    print(f"vbagent import time: {result.stdout.strip()}s")


def test_agents_module_import_is_fast():
    """Verify that importing vbagent.agents is fast."""
    result = subprocess.run(
        [sys.executable, "-c", """
import timeit
import sys

import_time = timeit.timeit(
    "from vbagent import agents",
    setup="import sys; [sys.modules.pop(k, None) for k in list(sys.modules) if k.startswith('vbagent')]",
    number=1,
)

print(f"{import_time:.4f}")
assert import_time < 0.5, f"Import too slow: {import_time:.4f}s"
"""],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed: {result.stderr}"
    print(f"vbagent.agents import time: {result.stdout.strip()}s")


def test_heavy_deps_not_loaded_on_import():
    """Verify heavy dependencies aren't loaded until needed."""
    result = subprocess.run(
        [sys.executable, "-c", """
import sys

# Clear modules
modules_to_clear = [k for k in sys.modules if k.startswith(('vbagent', 'openai', 'agents', 'pydantic'))]
for mod in modules_to_clear:
    sys.modules.pop(mod, None)

import vbagent

# These should NOT be loaded yet
assert 'openai' not in sys.modules, "openai loaded prematurely"
assert 'agents' not in sys.modules, "agents SDK loaded prematurely"

print("Heavy deps correctly deferred")
"""],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed: {result.stderr}"
    print("Heavy deps correctly deferred")


def test_classify_triggers_import():
    """Verify accessing classify loads the necessary modules."""
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
