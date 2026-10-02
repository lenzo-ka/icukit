"""Process-level settings and observability for detector caches.

The L3 implementation has no on-disk table store yet.  This module establishes the
stable public settings and counter surface used by compilation; L4 adds persistence
behind it without changing callers. One enable switch controls both the in-process
detector-gang memo and that table store: :func:`configure` overrides the environment
when passed ``enabled=True`` or ``False``; otherwise ``ICUKIT_CACHE=0`` is read at each
cache operation.
"""

from __future__ import annotations

import os
import sys
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Literal, TypeAlias

__all__ = ["StrPath", "cache_enabled", "cache_info", "configure", "flush"]

StrPath: TypeAlias = str | os.PathLike[str]

# sha256(b"icukit-l3-no-table-store-v1"); L4 replaces it with TableKey.digest().
_NO_TABLE_STORE_DIGEST = "bcf6ef899892ed05091edc292a8bca20e2b602211cab29e52603a4734ea786c2"
_PHASE: ContextVar[Literal["build", "detect"]] = ContextVar("icukit_cache_phase", default="detect")


def _default_root() -> Path:
    configured = os.environ.get("ICUKIT_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "icukit"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "icukit" / "Cache"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "icukit"


_enabled_override: bool | None = None
_root = _default_root()
_disabled_reason: str | None = None
_COUNTERS = {"compiles": 0, "compiled_reuse": 0, "detect_hits": 0}
_LOCK = threading.Lock()


def configure(*, enabled: bool | None = None, directory: StrPath | None = None) -> None:
    """Configure the process cache before constructing readers.

    L3 records the directory that the table store will use but does not create or read
    it. Passing ``True`` or ``False`` for ``enabled`` overrides ``ICUKIT_CACHE`` for
    both detector-gang memoization and the table store. Passing ``None`` leaves any
    existing override unchanged; without an override, the environment is read at each
    cache operation. A directory of ``None`` likewise leaves the root unchanged.
    """
    global _enabled_override, _root, _disabled_reason
    with _LOCK:
        if enabled is not None:
            _enabled_override = enabled
        if directory is not None:
            _root = Path(directory).expanduser()
        _disabled_reason = None


def cache_enabled() -> bool:
    """Return whether all detector caches are enabled for this call.

    An explicit :func:`configure` override wins. Until one is set, the
    ``ICUKIT_CACHE`` environment variable is read on every call so changing it to or
    from ``"0"`` takes effect without re-importing :mod:`icukit.cache`.
    """
    with _LOCK:
        override = _enabled_override
    return override if override is not None else os.environ.get("ICUKIT_CACHE") != "0"


def cache_info() -> dict:
    """Return process settings, zero table-store counts, and compile reuse counters.

    ``detect_hits`` counts compiled detects that made a compatible per-text scan plan
    available to the detect phase, not the number of readers or starts that used it.
    ``compiled_reuse`` counts gangs observed reusing their implicit compiled object.
    """
    enabled = cache_enabled()
    with _LOCK:
        counters = dict(_COUNTERS)
        return {
            "root": str(_root),
            "enabled": enabled,
            "disabled_reason": _disabled_reason,
            "table_store": _NO_TABLE_STORE_DIGEST,
            "entries": 0,
            "bytes": 0,
            "tables_loaded": {"build": 0, "detect": 0},
            "tables_computed": {"build": 0, "detect": 0},
            **counters,
        }


def flush() -> None:
    """Flush queued cache entries.

    There are no on-disk entries in L3, so this is intentionally a no-op.
    """


@contextmanager
def _build_phase():
    token = _PHASE.set("build")
    try:
        yield
    finally:
        _PHASE.reset(token)


def _record_compile() -> None:
    with _LOCK:
        _COUNTERS["compiles"] += 1


def _record_compiled_reuse() -> None:
    with _LOCK:
        _COUNTERS["compiled_reuse"] += 1


def _record_detect_hit() -> None:
    # The harness reads this hot-path counter from one worker thread. Detection never
    # depends on an exact multi-thread total; free-threaded Python is out of scope.
    _COUNTERS["detect_hits"] += 1


def _reset_counters() -> None:
    """Reset observability counters for isolated tests."""
    with _LOCK:
        for name in _COUNTERS:
            _COUNTERS[name] = 0
