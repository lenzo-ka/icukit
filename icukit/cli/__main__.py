"""Allow running icukit.cli as a module."""

from __future__ import annotations

import sys

from .main import main

sys.exit(main())
