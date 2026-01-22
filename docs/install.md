# Installation

icukit requires [PyICU](https://gitlab.pyicu.org/main/pyicu), a Python binding to the [ICU](https://icu.unicode.org/) library.

## macOS

```bash
pip install icukit
```

On macOS, icukit automatically installs `icukit-pyicu`, which bundles pre-built ICU libraries. No additional setup needed.

macOS does not expose system ICU headers, so the bundled approach is the only practical option.

## Linux

On Linux, icukit expects PyICU to be available. You have two options:

### Option 1: System ICU (Recommended)

Install your distribution's ICU development packages, then PyICU:

```bash
pip install icukit PyICU
```

This uses your system's ICU libraries, which is typically smaller and integrates better with system updates.

### Option 2: Bundled ICU

If you prefer a self-contained installation without system dependencies:

```bash
pip install icukit[bundled]
# or equivalently:
pip install icukit icukit-pyicu
```

This installs `icukit-pyicu` with pre-built ICU libraries.

### Installing System ICU Packages

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

### "No module named 'icu'" (Linux)

This means PyICU is not installed. Either:

```bash
# Install system ICU packages (see above), then:
pip install PyICU

# Or use bundled ICU:
pip install icukit[bundled]
```

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
