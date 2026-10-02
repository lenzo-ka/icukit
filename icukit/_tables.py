"""Trusted on-disk storage for expensive, deterministic detector tables.

The format uses :mod:`marshal`, so a cache root must be controlled by the same
user as the process. The embedded SHA-256 detects damage; it does not authenticate
crafted input.
"""

from __future__ import annotations

import atexit
import base64
import functools
import hashlib
import importlib
import importlib.metadata
import importlib.resources
import inspect
import json
import marshal
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from types import CodeType
from typing import TypeVar, cast

import icu

from . import cache

SCHEMA = 1
MAGIC = b"ICUKIT-TABLES\x01"
_VERSION_DIR = f"tables-v{SCHEMA}"
_T = TypeVar("_T")
_LOCK = threading.RLock()
_MEMORY: dict[tuple[str, tuple], object] = {}
_LOADED_SHARDS: set[tuple[str, str, str]] = set()
_QUEUED: dict[tuple[TableKey, tuple[str, str, str]], dict[tuple[str, tuple], bytes]] = {}
_REGISTRY: dict[str, Callable[..., object]] = {}
_KEY: TableKey | None = None
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class TableKey:
    """Every environment field on which a persisted table can depend.

    ``code`` hashes loader-read package modules (source, or bytecode for a
    sourceless install) and packaged data, including zip imports. ``tz`` hashes
    the sorted ICU zone-ID enumeration. ``icu_env`` records ``ICU_DATA`` and
    ``ICU_TIMEZONE_FILES_DIR``. ``default_locale`` separates ICU fallback results
    created under different process defaults.
    """

    schema: int
    icukit: str
    code: str
    icu: str
    pyicu: str
    pyicu_dist: str
    unicode: str
    cldr: str
    tz: str
    python_tag: str
    marshal: int
    py_unicode: str
    icu_env: str
    default_locale: str

    def json(self) -> str:
        """Return the canonical JSON stored beside every payload."""
        return json.dumps(asdict(self), ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    def digest(self) -> str:
        """Return SHA-256 over the canonical fields."""
        return hashlib.sha256(self.json().encode()).hexdigest()


def _field(name: str, source: Callable[[], object]) -> object:
    try:
        value = source()
        if value is None or value == "":
            raise ValueError("empty value")
        return value
    except Exception as error:
        cache._disable(f"TableKey.{name}: {type(error).__name__}: {error}")
        return "unknown"


def _walk_resources(node, prefix: str = "") -> Iterable[tuple[str, bytes]]:
    for child in node.iterdir():
        name = f"{prefix}/{child.name}" if prefix else child.name
        if child.is_dir():
            if child.name != "__pycache__":
                yield from _walk_resources(child, name)
        elif child.is_file():
            yield name, child.read_bytes()


def _code_hash(package: str = "icukit") -> str:
    """Hash package modules and data through its resource/loader abstraction."""
    root = importlib.resources.files(package)
    rows = list(_walk_resources(root))
    source = [(name, data) for name, data in rows if name.endswith(".py")]
    source_names = {name for name, _data in source}
    bytecode = [
        (name, data)
        for name, data in rows
        if name.endswith(".pyc") and name[:-1] not in source_names
    ]
    modules = [*source, *bytecode]
    data = [(name, value) for name, value in rows if name.startswith("data/")]
    selected = sorted((*modules, *data), key=lambda row: row[0])
    if not modules:
        raise ValueError(f"no module files found for {package}")
    digest = hashlib.sha256()
    for name, value in selected:
        encoded = name.encode("utf-8", "surrogateescape")
        digest.update(struct.pack(">I", len(encoded)))
        digest.update(encoded)
        digest.update(struct.pack(">Q", len(value)))
        digest.update(value)
    return digest.hexdigest()


def _tz_hash() -> str:
    identifiers = sorted(str(zone) for zone in icu.TimeZone.createEnumeration())
    return hashlib.sha256("\n".join(identifiers).encode()).hexdigest()


def table_key() -> TableKey:
    """Return the process table key; every individual source is total."""
    global _KEY
    with _LOCK:
        default_locale = cast(
            str,
            _field("default_locale", lambda: icu.Locale.getDefault().getName()),
        )
        if _KEY is not None:
            if _KEY.default_locale == default_locale:
                return _KEY
            return replace(_KEY, default_locale=default_locale)
        package = importlib.import_module("icukit")
        _KEY = TableKey(
            schema=SCHEMA,
            icukit=cast(str, _field("icukit", lambda: package.__version__)),
            code=cast(str, _field("code", _code_hash)),
            icu=cast(str, _field("icu", lambda: icu.ICU_VERSION)),
            pyicu=cast(str, _field("pyicu", lambda: icu.VERSION)),
            pyicu_dist=cast(
                str,
                _field("pyicu_dist", lambda: importlib.metadata.version("icukit-pyicu")),
            ),
            unicode=cast(str, _field("unicode", lambda: icu.UNICODE_VERSION)),
            cldr=cast(
                str,
                _field(
                    "cldr",
                    lambda: icu.ResourceBundle("", icu.Locale("root")).get("Version").getString(),
                ),
            ),
            tz=cast(str, _field("tz", _tz_hash)),
            python_tag=cast(str, _field("python_tag", lambda: sys.implementation.cache_tag)),
            marshal=cast(int, _field("marshal", lambda: marshal.version)),
            py_unicode=cast(str, _field("py_unicode", lambda: unicodedata.unidata_version)),
            icu_env=cast(
                str,
                _field(
                    "icu_env",
                    lambda: json.dumps(
                        {
                            "ICU_DATA": os.environ.get("ICU_DATA", ""),
                            "ICU_TIMEZONE_FILES_DIR": os.environ.get("ICU_TIMEZONE_FILES_DIR", ""),
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                ),
            ),
            default_locale=default_locale,
        )
        return _KEY


def _allowed(value: object, seen: set[int] | None = None) -> bool:
    if isinstance(value, CodeType):
        return False
    if type(value) in {str, int, bool, type(None)}:
        return True
    if type(value) not in {tuple, list, frozenset, dict}:
        return False
    seen = set() if seen is None else seen
    marker = id(value)
    if marker in seen:
        return False
    seen.add(marker)
    if isinstance(value, dict):
        valid = all(_allowed(key, seen) and _allowed(item, seen) for key, item in value.items())
    else:
        valid = all(_allowed(item, seen) for item in value)
    seen.remove(marker)
    return valid


def _language(args: tuple) -> str:
    if not args or not isinstance(args[0], str):
        return "_"
    language = icu.Locale(args[0]).getLanguage()
    return _SAFE_NAME.sub("_", language) or "_"


def _qualname(name: str) -> str:
    return _SAFE_NAME.sub("_", name)


def _paths(digest: str, qualname: str, language: str) -> tuple[Path, Path]:
    _enabled, root, _reason = cache._settings()
    directory = root / _VERSION_DIR / digest / _qualname(qualname)
    return directory / f"{language}.tables", directory / f"{language}.lock"


def _encode(entries: dict[tuple[str, tuple], object], key: TableKey) -> bytes:
    if not _allowed(entries):
        raise ValueError("table payload contains an unsupported type")
    payload = marshal.dumps(entries)
    key_json = key.json().encode()
    return b"".join(
        (
            MAGIC,
            struct.pack(">I", len(key_json)),
            key_json,
            hashlib.sha256(payload).digest(),
            payload,
        )
    )


def _decode(data: bytes, key: TableKey) -> dict[tuple[str, tuple], object] | None:
    minimum = len(MAGIC) + 4 + 32
    if len(data) < minimum or not data.startswith(MAGIC):
        return None
    offset = len(MAGIC)
    key_length = struct.unpack(">I", data[offset : offset + 4])[0]
    offset += 4
    if len(data) < offset + key_length + 32:
        return None
    key_json = data[offset : offset + key_length]
    offset += key_length
    expected = data[offset : offset + 32]
    payload = data[offset + 32 :]
    if key_json != key.json().encode() or hashlib.sha256(payload).digest() != expected:
        return None
    try:
        entries = marshal.loads(payload)
    except (EOFError, TypeError, ValueError):
        return None
    if type(entries) is not dict or not _allowed(entries):
        return None
    for entry, value in entries.items():
        if (
            type(entry) is not tuple
            or len(entry) != 2
            or type(entry[0]) is not str
            or type(entry[1]) is not tuple
            or not _allowed(value)
        ):
            return None
    return entries


def _read(path: Path, key: TableKey, operation: str) -> dict[tuple[str, tuple], object]:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return {}
    except OSError as error:
        cache._disable(f"{operation} {path}: {type(error).__name__}: {error}")
        return {}
    return _decode(data, key) or {}


def _prepare_directory(path: Path, operation: str) -> bool:
    try:
        _enabled, root, _disabled = cache._settings()
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(path, 0o700)
        return True
    except OSError as error:
        cache._disable(f"{operation} {path}: {type(error).__name__}: {error}")
        return False


def _lock_file(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        if handle.read(1) == b"":
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def persisted(function: Callable[..., _T]) -> Callable[..., _T]:
    """Memoize and persist one pure function whose arguments and result marshal."""
    signature = inspect.signature(function)
    name = function.__qualname__
    _REGISTRY[name] = function

    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        call_args = tuple(bound.arguments[parameter] for parameter in signature.parameters)
        entry = (name, call_args)
        enabled, _root, disabled = cache._settings()
        if not enabled:
            return function(*args, **kwargs)
        with _LOCK:
            if entry in _MEMORY:
                if cache._PHASE.get() == "detect":
                    cache._record_table_detect_hit()
                return cast(_T, _MEMORY[entry])
        enabled = disabled is None
        key = table_key() if enabled else None
        enabled = enabled and cache._settings()[2] is None
        language = "_"
        if enabled:
            try:
                assert key is not None
                language = _language(call_args)
                shard = (key.digest(), name, language)
                with _LOCK:
                    first_read = shard not in _LOADED_SHARDS
                    if first_read:
                        _LOADED_SHARDS.add(shard)
                if first_read:
                    path, _lock = _paths(*shard)
                    loaded = _read(path, key, "read")
                    with _LOCK:
                        _MEMORY.update(loaded)
                    cache._record_table("tables_loaded", len(loaded))
                with _LOCK:
                    if entry in _MEMORY:
                        return cast(_T, _MEMORY[entry])
            except Exception as error:
                cache._disable(f"load {name}: {type(error).__name__}: {error}")
                enabled = False
        value = function(*args, **kwargs)
        cache._record_table("tables_computed")
        with _LOCK:
            _MEMORY[entry] = value
        if enabled:
            try:
                assert key is not None
                if not _allowed(call_args) or not _allowed(value):
                    raise TypeError("arguments or result contain an unsupported type")
                snapshot = marshal.dumps(value)
                shard = (key.digest(), name, language)
                with _LOCK:
                    _QUEUED.setdefault((key, shard), {})[entry] = snapshot
            except Exception as error:
                cache._disable(f"queue {name}: {type(error).__name__}: {error}")
        return value

    wrapped.__persisted_original__ = function  # type: ignore[attr-defined]
    return wrapped


def flush() -> None:
    """Merge every queued snapshot into its shard under an interprocess lock."""
    enabled, _root, disabled = cache._settings()
    if not enabled or disabled is not None:
        return
    with _LOCK:
        pending = dict(_QUEUED)
        _QUEUED.clear()
    for (key, shard), snapshots in pending.items():
        path, lock_path = _paths(*shard)
        if not _prepare_directory(path.parent, "mkdir"):
            return
        temporary: str | None = None
        try:
            with lock_path.open("a+b") as lock:
                _lock_file(lock)
                try:
                    merged = _read(path, key, "re-read")
                    if cache._settings()[2] is not None:
                        return
                    for entry, snapshot in snapshots.items():
                        value = marshal.loads(snapshot)
                        if not _allowed(value):
                            raise ValueError("queued snapshot contains an unsupported type")
                        merged[entry] = value
                    encoded = _encode(merged, key)
                    with tempfile.NamedTemporaryFile(
                        mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
                    ) as output:
                        temporary = output.name
                        output.write(encoded)
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(temporary, path)
                    temporary = None
                finally:
                    _unlock_file(lock)
        except Exception as error:
            cache._disable(f"flush {path}: {type(error).__name__}: {error}")
            return
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass


def _current_files() -> list[Path]:
    key = table_key()
    _enabled, root, _disabled = cache._settings()
    base = root / _VERSION_DIR / key.digest()
    try:
        return sorted(base.glob("*/*.tables")) if base.is_dir() else []
    except OSError as error:
        cache._disable(f"list {base}: {type(error).__name__}: {error}")
        return []


def list_entries() -> list[dict[str, object]]:
    """List current-environment shards without changing them."""
    key = table_key()
    rows = []
    for path in _current_files():
        entries = _read(path, key, "list")
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        rows.append({"path": str(path), "entries": len(entries), "bytes": size})
    return rows


def clear() -> None:
    """Remove every icukit table-store generation below the configured root."""
    _enabled, root, _disabled = cache._settings()
    target = root / _VERSION_DIR
    try:
        if target.exists():
            shutil.rmtree(target)
    except OSError as error:
        cache._disable(f"clear {target}: {type(error).__name__}: {error}")
    _reconfigure()


def prune() -> None:
    """Remove table-key directories other than the current environment's."""
    key = table_key()
    _enabled, root, _disabled = cache._settings()
    target = root / _VERSION_DIR
    try:
        if target.is_dir():
            for child in target.iterdir():
                if child.is_dir() and child.name != key.digest():
                    shutil.rmtree(child)
    except OSError as error:
        cache._disable(f"prune {target}: {type(error).__name__}: {error}")


def _same(left: object, right: object) -> bool:
    """Compare persisted values exactly, including types, order, and repr."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        left_items = list(left.items())
        right_items = list(cast(dict, right).items())
        return len(left_items) == len(right_items) and all(
            _same(a_key, b_key) and _same(a_value, b_value)
            for (a_key, a_value), (b_key, b_value) in zip(left_items, right_items, strict=True)
        )
    if isinstance(left, (list, tuple)):
        other = cast(list | tuple, right)
        return len(left) == len(other) and all(
            _same(a, b) for a, b in zip(left, other, strict=True)
        )
    if isinstance(left, frozenset):
        return sorted(map(repr, left)) == sorted(map(repr, cast(frozenset, right)))
    return left == right and repr(left) == repr(right)


def _recompute(entry: tuple[str, tuple]) -> object:
    importlib.import_module("icukit.recognize")
    name, args = entry
    return _REGISTRY[name](*args)


def verify() -> tuple[int, list[str]]:
    """Recompute every current entry in one fresh cache-disabled subprocess."""
    key = table_key()
    failures: list[str] = []
    stored: list[tuple[Path, tuple[str, tuple], object]] = []
    for path in _current_files():
        try:
            data = path.read_bytes()
        except OSError as error:
            failures.append(f"{path}: unreadable shard: {type(error).__name__}: {error}")
            continue
        entries = _decode(data, key)
        if entries is None:
            failures.append(f"{path}: invalid shard")
            continue
        for entry, expected in entries.items():
            stored.append((path, entry, expected))
    if not stored:
        return 0, failures
    request = base64.urlsafe_b64encode(
        marshal.dumps(tuple(entry for _, entry, _ in stored))
    ).decode()
    environment = {**os.environ, "ICUKIT_CACHE": "0"}
    result = subprocess.run(
        [sys.executable, "-c", "from icukit._tables import _worker_many; _worker_many()"],
        env=environment,
        text=True,
        capture_output=True,
        input=request,
    )
    prefix = "ICUKIT-TABLE-RESULT "
    line = next((row for row in result.stdout.splitlines() if row.startswith(prefix)), None)
    if result.returncode or line is None:
        failures.extend(f"{path}: {entry!r}: recompute failed" for path, entry, _ in stored)
        return len(stored), failures
    try:
        actual_values = marshal.loads(base64.urlsafe_b64decode(line.removeprefix(prefix)))
    except Exception:
        failures.extend(
            f"{path}: {entry!r}: invalid subprocess result" for path, entry, _ in stored
        )
        return len(stored), failures
    if type(actual_values) is not tuple or len(actual_values) != len(stored):
        failures.extend(
            f"{path}: {entry!r}: invalid subprocess result" for path, entry, _ in stored
        )
        return len(stored), failures
    for (path, entry, expected), actual in zip(stored, actual_values, strict=True):
        if not _same(expected, actual):
            failures.append(f"{path}: {entry!r}: mismatch")
    return len(stored), failures


def _worker_many() -> None:
    """Read a marshal request on stdin and emit recomputed values for verification."""
    request = marshal.loads(base64.urlsafe_b64decode(sys.stdin.read()))
    values = tuple(_recompute(entry) for entry in request)
    encoded = base64.urlsafe_b64encode(marshal.dumps(values)).decode()
    print("ICUKIT-TABLE-RESULT " + encoded)


def _store_info() -> dict[str, object]:
    key = table_key()
    entries = 0
    size = 0
    for path in _current_files():
        decoded = _read(path, key, "cache_info")
        entries += len(decoded)
        try:
            size += path.stat().st_size
        except OSError:
            pass
    enabled, _root, disabled = cache._settings()
    return {
        "table_store": key.digest(),
        "entries": entries,
        "bytes": size,
        "enabled": enabled and disabled is None,
        "disabled_reason": disabled,
    }


def _reconfigure() -> None:
    global _KEY
    with _LOCK:
        _clear_memory()
        _QUEUED.clear()
        _KEY = None


def _clear_memory() -> None:
    """Drop loaded table values without touching queued snapshots or disk files."""
    with _LOCK:
        _MEMORY.clear()
        _LOADED_SHARDS.clear()


def _main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] in {"--recompute", "--recompute-many"}:
        try:
            request = marshal.loads(base64.urlsafe_b64decode(sys.argv[2]))
            value = (
                tuple(_recompute(entry) for entry in request)
                if sys.argv[1] == "--recompute-many"
                else _recompute(request)
            )
            print("ICUKIT-TABLE-RESULT " + base64.urlsafe_b64encode(marshal.dumps(value)).decode())
            return 0
        except Exception as error:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
            return 1
    return 2


atexit.register(flush)


if __name__ == "__main__":
    raise SystemExit(_main())
