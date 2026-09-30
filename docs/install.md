# Installation

icukit is built on [PyICU](https://gitlab.pyicu.org/main/pyicu), a Python
binding to the [ICU](https://icu.unicode.org/) library. By default it installs
[`icukit-pyicu`](https://github.com/lenzo-ka/icukit-pyicu), which bundles
pre-built ICU libraries together with PyICU, so there is nothing else to set up.

## macOS and Linux

```bash
pip install icukit
```

`icukit-pyicu` ships self-contained wheels for both platforms:

- **macOS** — Apple Silicon (`arm64`, macOS 11+)
- **Linux** — `x86_64` (manylinux, glibc 2.35+) and `aarch64` (glibc 2.38+)

for CPython 3.9 through 3.14. No system ICU packages, compilers, or headers are
required.

icukit itself requires Python 3.11 or later, and its CI tests Python 3.11 through
3.13, so the `icukit-pyicu` wheels cover more versions than icukit uses.

## Verifying Installation

After installation, verify everything works:

```bash
python -c "import icukit; print('icukit version:', icukit.__version__)"
python -c "import icu; print('ICU', icu.ICU_VERSION, '| PyICU', icu.VERSION)"
```

Or test from the CLI:

```bash
ik --version
ik locale info en_US
```

## Cartlet sentence model

Cartlet 0.7.0 or later is an icukit dependency and is installed by the normal
icukit installation above once the owner's cartlet 0.7.0 release is available
from PyPI. English `SentenceOverride` instances use the `en-tn-cart@1`
sentence-break base by default:

```bash
python -c 'from icukit import SentenceOverride; SentenceOverride()'
```

Cartlet is imported lazily, only when a cartlet model is selected. The English
`POSIX` locale variant defaults to `base="none"` because its ICU word tokens
differ from the model profile. Explicit `SentenceOverride(base="none")` and
non-English locale defaults therefore do not pay its import cost.

## Advanced: using a system PyICU

`icukit-pyicu` and system [PyICU](https://gitlab.pyicu.org/main/pyicu) both
provide the same importable `icu` module, so either satisfies icukit at runtime.
If you would rather build PyICU against your own system ICU (for example on a
platform without a bundled wheel, such as an older glibc or a distro not covered
above), install PyICU first and then install icukit without its dependencies:

```bash
# Install system ICU development packages, e.g.:
sudo apt install libicu-dev pkg-config     # Ubuntu/Debian
sudo dnf install libicu-devel pkg-config   # Fedora/RHEL
sudo pacman -S icu                         # Arch Linux

pip install PyICU
pip install --no-deps icukit
```

## Troubleshooting

### Both `icukit-pyicu` and `PyICU` installed

Both packages provide the same `icu` module, so only one should be installed. If
you end up with both and hit import issues, remove one:

```bash
pip uninstall icukit-pyicu   # keep system PyICU
# or
pip uninstall PyICU          # keep the bundled ICU
```
