# Releasing icukit

*Maintainer release checklist. This file ships in the source distribution but is not part of the user-facing documentation set.*

Publishing is automated by `.github/workflows/publish.yml` using PyPI Trusted Publishing. Publishing a GitHub Release builds and uploads the distribution without an API token.

## One-time setup

- On PyPI, update the `icukit` trusted publisher to owner `lenzo-ka`, repository `icukit`, workflow `publish.yml`, and environment `pypi`. The existing publisher names `ci.yml` and will not authorize the new workflow.
- In the GitHub repository, create the `pypi` environment if it does not already exist. The publish job references it, and the OIDC identity is scoped to it.

## Cutting a release

1. Set `__version__ = "X.Y.Z"` in `icukit/__init__.py`. `pyproject.toml` reads the package version from that attribute through setuptools; do not set a second version there.
2. Head the changelog before building. Replace `UNRELEASED` in `## [X.Y.Z] - UNRELEASED` with the tag day in `YYYY-MM-DD` form, leave a fresh empty `## [Unreleased]` above it, retarget the `[Unreleased]` comparison to `vX.Y.Z...HEAD`, and add the release comparison from the previous tag to `vX.Y.Z`.
3. Verify the release candidate from the development environment:

   Install `actionlint` separately through a system package manager; skip its command below when it is unavailable.

   ```bash
   uv run --extra dev ruff check .
   uv run --extra dev ruff format --check .
   uv run --extra dev python docs/generate.py --check
   uv run --extra dev python -m pytest tests/ -q
   TIERGRAPH_FLOOR=$(sed -n 's/.*"tiergraph>=\([0-9][0-9.]*\).*/\1/p' pyproject.toml | head -n 1)
   uv run --extra dev --with "tiergraph==$TIERGRAPH_FLOOR" python -m pytest tests/test_tiergraph_text_example.py -q
   actionlint .github/workflows/*.yml
   uv run --extra dev --with build python -m build
   ls -1 dist
   unzip -l dist/*.whl
   uv run --extra dev python -c "import icukit; print(icukit.__version__)"
   ```

   `ls` must show only `icukit-X.Y.Z.tar.gz` and `icukit-X.Y.Z-py3-none-any.whl`. Read the wheel listing to confirm that it contains the `icukit` package and its data. The printed version, filenames, and intended tag must agree. Remove `dist/`, `build/`, and `icukit.egg-info/` after inspection.
4. Commit the version and changelog changes, then tag that commit `vX.Y.Z` and push the commit and tag after CI passes.
5. Create and publish a GitHub Release for `vX.Y.Z`. Publishing the release triggers `.github/workflows/publish.yml`, which builds the source distribution and pure-Python wheel, checks the tag against `icukit.__version__`, and uploads through PyPI Trusted Publishing.
6. In a fresh virtual environment, run `pip install icukit==X.Y.Z` and confirm `python -c "import icukit; print(icukit.__version__)"` prints `X.Y.Z`.

## Notes and gotchas

- The release tag must be `v` followed by the value of `icukit.__version__`; the publish build fails on a mismatch.
- PyPI files are immutable. Correct a bad build with a new version rather than attempting to replace it.
- A published consumer should depend on a released icukit version with a compatibility bound appropriate to that consumer. A dependency on a Git branch cannot be published to PyPI.
- The normal CI test job uses the released tiergraph constraint from the development extra. The separate tiergraph integration job checks out tiergraph's main branch as an upstream compatibility canary.
- The candidate check pins the lowest tiergraph the development constraint admits, read out of `pyproject.toml` rather than written into this file. A version written here would go stale the moment the constraint moved, and the stale pin would still pass.
