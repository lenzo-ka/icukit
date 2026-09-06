# Local development Makefile - not for distribution

VENV := venv
PIP := $(VENV)/bin/pip

# Prefer a local virtual environment when `make venv` has created one, and fall
# back to uv otherwise. Continuous integration and the release checklist both
# provision the development environment through uv, so a tree that has never run
# `make venv` still has a working interpreter here. Override PYTHON to force one.
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,uv run --extra dev python)

.PHONY: venv
venv:
	python3 -m venv $(VENV)

.PHONY: install
install: venv
	$(PIP) install -e ".[dev]"

.PHONY: test
test:
	$(PYTHON) -m pytest

.PHONY: docs
docs:
	$(PYTHON) docs/generate.py

.PHONY: docs-check
docs-check:
	$(PYTHON) docs/generate.py --check

.PHONY: clean
clean:
	rm -rf build/ dist/ *.egg-info/ icukit_kal.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
