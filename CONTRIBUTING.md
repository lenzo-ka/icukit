# Contributing

## Tests

The default `pytest` configuration deselects tests marked `slow`, including the
exhaustive 64 KiB pathological-input and scaling matrix. Run the ordinary and slow
suites separately for a full local test gate:

```bash
pytest
pytest -m slow
```

The remaining project checks are:

```bash
ruff check .
ruff format --check .
python docs/generate.py --check
```
