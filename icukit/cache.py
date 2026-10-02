"""Process-level settings and observability for detector caches.

The first use of an expensive, registered detector table stores a local snapshot;
no prebuilt tables ship in the wheel. The root is ``ICUKIT_CACHE_DIR`` when set,
then the platform cache directory. It can instead be selected with
:func:`configure` before readers are built. The root is created with mode ``0700``.

The directory must be trusted. Table files use :mod:`marshal`; their SHA-256
detects accidental damage but does not authenticate crafted input. The key covers
icukit code and data, ICU, PyICU, CLDR, Unicode, Python, the ICU data environment,
the ICU default locale, and a hash of the available time-zone IDs. A residual risk
remains: zone display data can change without the wheel version or zone-ID set
changing. Run ``ik compile --verify`` to recompute and compare every entry.

Only registered, deterministic Python tables are serialized. ICU objects, detector
instances, and application material remain in memory. Disable all disk reads and
writes with ``configure(enabled=False)``, ``ICUKIT_CACHE=0``, or
``ik detect --no-cache``. :func:`flush` writes queued marshal snapshots explicitly;
process exit is only a fallback.
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
_COUNTERS = {
    "compiles": 0,
    "compiled_reuse": 0,
    "detect_hits": 0,
    "table_detect_hits": 0,
}
_TABLE_COUNTERS = {
    "tables_loaded": {"build": 0, "detect": 0},
    "tables_computed": {"build": 0, "detect": 0},
}
_LOCK = threading.RLock()


def configure(*, enabled: bool | None = None, directory: StrPath | None = None) -> None:
    """Configure the process cache before constructing readers.

    Passing ``True`` or ``False`` for ``enabled`` overrides ``ICUKIT_CACHE`` for the
    in-process detector caches and the table store. Without an override, the
    environment is read at each cache operation. Passing ``None`` leaves the
    corresponding setting unchanged. Reconfiguration drops process-local table
    snapshots so a newly selected directory is populated from the real table builders.
    A configured directory must be trusted because table files use :mod:`marshal`.
    """
    global _enabled_override, _root, _disabled_reason
    with _LOCK:
        if enabled is not None:
            _enabled_override = enabled
        if directory is not None:
            _root = Path(directory).expanduser()
        _disabled_reason = None
    try:
        from . import _tables

        _tables._reconfigure()
    except ImportError:
        pass


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
    """Return process settings, table-store counts, and compile reuse counters.

    ``detect_hits`` counts compiled detects that made a compatible per-text scan plan
    available to the detect phase, not the number of readers or starts that used it.
    ``table_detect_hits`` counts persisted table entries reused during the detect phase.
    ``compiled_reuse`` counts gangs observed reusing their implicit compiled object.
    """
    enabled = cache_enabled()
    with _LOCK:
        result = {
            "root": str(_root),
            "enabled": enabled and _disabled_reason is None,
            "disabled_reason": _disabled_reason,
            "tables_loaded": dict(_TABLE_COUNTERS["tables_loaded"]),
            "tables_computed": dict(_TABLE_COUNTERS["tables_computed"]),
            **_COUNTERS,
        }
    if not result["enabled"]:
        result.update({"table_store": None, "entries": 0, "bytes": 0})
        return result
    try:
        from . import _tables

        result.update(_tables._store_info())
    except Exception as error:
        _disable(f"cache_info: {type(error).__name__}: {error}")
        result.update({"table_store": None, "entries": 0, "bytes": 0})
        with _LOCK:
            result["enabled"] = False
            result["disabled_reason"] = _disabled_reason
    return result


def flush() -> None:
    """Write every queued table snapshot now."""
    try:
        from . import _tables

        _tables.flush()
    except Exception as error:
        _disable(f"flush: {type(error).__name__}: {error}")


@contextmanager
def _build_phase():
    token = _PHASE.set("build")
    try:
        yield
    finally:
        _PHASE.reset(token)


def _settings() -> tuple[bool, Path, str | None]:
    with _LOCK:
        root = _root
        disabled_reason = _disabled_reason
    return cache_enabled(), root, disabled_reason


def _disable(reason: str) -> None:
    global _disabled_reason
    with _LOCK:
        if _disabled_reason is None:
            _disabled_reason = reason


def _record_table(kind: Literal["tables_loaded", "tables_computed"], count: int = 1) -> None:
    with _LOCK:
        _TABLE_COUNTERS[kind][_PHASE.get()] += count


def _table_counts() -> tuple[int, int]:
    with _LOCK:
        return (
            sum(_TABLE_COUNTERS["tables_loaded"].values()),
            sum(_TABLE_COUNTERS["tables_computed"].values()),
        )


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


def _record_table_detect_hit() -> None:
    # This has the same single-worker observability contract as ``detect_hits``.
    _COUNTERS["table_detect_hits"] += 1


def _reset_counters() -> None:
    """Reset observability counters for isolated tests."""
    with _LOCK:
        for name in _COUNTERS:
            _COUNTERS[name] = 0
        for phases in _TABLE_COUNTERS.values():
            phases["build"] = phases["detect"] = 0
