# Installation

icukit requires [PyICU](https://gitlab.pyicu.org/main/pyicu), a Python binding to the [ICU](https://icu.unicode.org/) library.

## macOS

```bash
pip install icukit
```

On macOS, icukit automatically installs `icukit-pyicu`, which bundles pre-built ICU libraries. No additional setup needed.

macOS does not expose system ICU headers, so the bundled approach is the only practical option.

## Linux

On Linux, icukit automatically installs PyICU, which builds against your system's ICU libraries.

First, install the ICU development packages for your distribution:

**Ubuntu/Debian:**
```bash
sudo apt install libicu-dev pkg-config
```

**Fedora/RHEL:**
```bash
sudo dnf install libicu-devel pkg-config
```

**Arch Linux:**
```bash
sudo pacman -S icu
```

Then install icukit:

```bash
pip install icukit
```

### Alternative: Bundled ICU

If you prefer a self-contained installation without system ICU dependencies:

```bash
pip install icukit[bundled]
```

This installs `icukit-pyicu` instead of PyICU, with pre-built ICU libraries included.

## Verifying Installation

After installation, verify everything works:

```bash
python -c "import icukit; print('icukit version:', icukit.__version__)"
```

Or test from the CLI:

```bash
ik --version
ik locale info en_US
```

## Troubleshooting

### PyICU build fails on Linux

Make sure you have the ICU development headers installed:

```bash
# Check if icu-config is available
icu-config --version

# If not, install the dev package for your distro (see above)
```

### Version conflicts

If you have both `icukit-pyicu` and `PyICU` installed and encounter issues, you can remove one:

```bash
pip uninstall icukit-pyicu  # keep system PyICU
# or
pip uninstall PyICU  # keep bundled
```

Both packages provide the same `icu` module, so only one should be installed.
