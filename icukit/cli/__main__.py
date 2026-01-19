"""Allow running icukit.cli as a module."""

import sys

from .main import main

sys.exit(main())
