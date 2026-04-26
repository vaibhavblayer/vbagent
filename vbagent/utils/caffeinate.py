"""Prevent system sleep during long-running operations.

macOS: uses `caffeinate` command
Linux: uses `systemd-inhibit` if available, else `xdg-screensaver`
Windows: uses `SetThreadExecutionState` via ctypes
"""

from __future__ import annotations

import subprocess
import sys
from contextlib import contextmanager
from typing import Optional


@contextmanager
def prevent_sleep(reason: str = "vbagent long-running operation"):
    """Context manager that prevents the system from sleeping.

    Usage:
        with prevent_sleep("Rendering animation"):
            # ... long operation ...

    Silently does nothing if the platform isn't supported or the
    command isn't available.
    """
    proc: Optional[subprocess.Popen] = None

    try:
        if sys.platform == "darwin":
            # macOS: caffeinate -i (prevent idle sleep)
            proc = subprocess.Popen(
                ["caffeinate", "-i", "-w", str(__import__("os").getpid())],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif sys.platform == "linux":
            # Linux: try systemd-inhibit first
            try:
                proc = subprocess.Popen(
                    [
                        "systemd-inhibit",
                        "--what=idle",
                        f"--reason={reason}",
                        "sleep", "infinity",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                # Fallback: xdg-screensaver suspend (needs a window ID, skip if not available)
                proc = None
        elif sys.platform == "win32":
            # Windows: prevent sleep via SetThreadExecutionState
            try:
                import ctypes
                ES_CONTINUOUS = 0x80000000
                ES_SYSTEM_REQUIRED = 0x00000001
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED
                )
            except Exception:
                pass

        yield

    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        if sys.platform == "win32":
            try:
                import ctypes
                ES_CONTINUOUS = 0x80000000
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            except Exception:
                pass
