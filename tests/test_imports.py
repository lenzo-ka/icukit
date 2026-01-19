"""Test that all public API imports work correctly."""

from importlib import import_module


class TestImports:
    """Test that icukit modules and exports can be imported."""

    def test_main_package_import(self):
        """Test that the main package can be imported."""
        import icukit

        assert icukit.__version__ is not None

    def test_core_module_imports(self):
        """Test that core modules can be imported directly."""
        modules = [
            "icukit.errors",
            "icukit.transliterator",
        ]
        for module_name in modules:
            module = import_module(module_name)
            assert module is not None

    def test_class_imports_from_modules(self):
        """Test that main classes can be imported from their modules."""
        imports = [
            ("icukit.transliterator", "Transliterator"),
            ("icukit.transliterator", "CommonTransliterators"),
            ("icukit.errors", "ICUKitError"),
        ]
        for module_name, class_name in imports:
            module = import_module(module_name)
            cls = getattr(module, class_name)
            assert cls is not None

    def test_public_api_imports(self):
        """Test that all public API symbols can be imported from icukit."""
        from icukit import (  # noqa: F401
            CommonTransliterators,
            FormatError,
            ICUKitError,
            LocaleError,
            ParseError,
            PatternError,
            Transliterator,
            list_transliterators,
            transliterate,
        )

        assert Transliterator is not None
        assert transliterate is not None

    def test_cli_module_imports(self):
        """Test that CLI modules can be imported."""
        cli_modules = [
            "icukit.cli",
            "icukit.cli.main",
            "icukit.cli.command_trie",
            "icukit.cli.base",
            "icukit.cli.output_helpers",
            "icukit.cli.locale_helpers",
            "icukit.cli.command",
            "icukit.cli.command.transliterate",
            "icukit.cli.command.regex",
            "icukit.cli.command.script",
            "icukit.cli.command.unicode",
            "icukit.cli.command.region",
            "icukit.cli.command.discover",
        ]
        for module_name in cli_modules:
            module = import_module(module_name)
            assert module is not None
