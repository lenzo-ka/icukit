# Local development Makefile - not for distribution

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

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
