"""Suite-wide isolation for process-level table caching."""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile

_CACHE_ROOT = tempfile.mkdtemp(prefix="icukit-test-cache-")
os.environ["ICUKIT_CACHE_DIR"] = _CACHE_ROOT
atexit.register(shutil.rmtree, _CACHE_ROOT, ignore_errors=True)
