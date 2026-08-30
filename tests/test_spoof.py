"""Tests for spoof/confusable detection module and CLI."""

import json
import subprocess
import sys

from icukit import (
    CONFUSABLE_MIXED_SCRIPT,
    CONFUSABLE_NONE,
    SpoofChecker,
    are_confusable,
    check_string,
    get_confusable_info,
    get_confusable_type,
    get_skeleton,
)


class TestSpoofLibrary:
    """Tests for spoof library functions."""

    def test_are_confusable_true(self):
        """Test confusable strings."""
        # Cyrillic 'а' vs Latin 'a'
        assert are_confusable("paypal", "pаypal") is True

    def test_are_confusable_false(self):
        """Test non-confusable strings."""
        assert are_confusable("hello", "world") is False

    def test_are_confusable_identical(self):
        """Test identical strings."""
        assert are_confusable("hello", "hello") is True

    def test_get_confusable_type_none(self):
        """Test confusable type for non-confusable."""
        result = get_confusable_type("hello", "world")
        assert result == CONFUSABLE_NONE

    def test_get_confusable_type_mixed(self):
        """Test confusable type for mixed script."""
        result = get_confusable_type("paypal", "pаypal")
        assert result & CONFUSABLE_MIXED_SCRIPT

    def test_get_skeleton(self):
        """Test skeleton generation."""
        skel1 = get_skeleton("paypal")
        skel2 = get_skeleton("pаypal")  # Cyrillic а
        assert skel1 == skel2

    def test_check_string_clean(self):
        """Test check on clean string."""
        result = check_string("hello")
        assert result["is_suspicious"] is False

    def test_check_string_suspicious(self):
        """Test check on suspicious string."""
        result = check_string("pаypal")  # Cyrillic а
        assert result["is_suspicious"] is True

    def test_check_string_names_the_check_that_fired_on_a_mixed_script_identifier(self):
        """``is_suspicious`` alone leaves the module free to be right for the wrong reason.

        A single-string check does not answer the pairwise question, so ICU does
        not set the confusability flags here however lookalike the string is; what
        it sets is the restriction level, because the default identifier profile
        does not admit an identifier mixing Latin and Cyrillic. Asserting only the
        summary let the docstring claim ``mixed_script`` was True for years.
        """
        result = check_string("pаypal")  # Cyrillic а
        assert result["restriction_level"] is True
        assert result["mixed_script"] is False
        assert result["whole_script"] is False

    def test_confusability_is_the_pairwise_question_a_single_string_check_cannot_answer(self):
        """The same pair, asked the other way, does report mixed-script confusability."""
        assert get_confusable_type("paypal", "pаypal") & CONFUSABLE_MIXED_SCRIPT
        assert check_string("pаypal")["mixed_script"] is False

    def test_check_string_reports_a_hidden_overlay(self):
        """An "i" followed by U+0307 renders as a plain dotted i, hiding the mark it carries.

        This is the witness that holds ``_CHECK_HIDDEN_OVERLAY`` to ICU's own
        answer. PyICU's ``USpoofChecks`` does not expose the name, so the module
        falls back to a literal; the literal is only correct while ICU reports
        exactly this bit for exactly this case, and that is what is asserted here
        rather than assumed. A clean string must not set it, or the field would be
        satisfied by any bit at all.
        """
        overlaid = check_string("i̇")
        assert overlaid["hidden_overlay"] is True
        assert overlaid["is_suspicious"] is True
        assert check_string("hello")["hidden_overlay"] is False

    def test_get_confusable_info(self):
        """Test detailed confusable info."""
        info = get_confusable_info("paypal", "pаypal")
        assert info["confusable"] is True
        assert info["same_skeleton"] is True
        assert "mixed_script" in info["type_names"]


class TestSpoofChecker:
    """Tests for SpoofChecker class."""

    def test_init(self):
        """Test checker initialization."""
        checker = SpoofChecker()
        assert checker is not None

    def test_are_confusable(self):
        """Test are_confusable method."""
        checker = SpoofChecker()
        assert checker.are_confusable("paypal", "pаypal") is True
        assert checker.are_confusable("hello", "world") is False

    def test_get_skeleton(self):
        """Test get_skeleton method."""
        checker = SpoofChecker()
        assert checker.get_skeleton("pаypal") == "paypal"

    def test_check(self):
        """Test check method."""
        checker = SpoofChecker()
        result = checker.check("pаypal")
        assert result["is_suspicious"] is True

    def test_check_reports_the_same_record_as_the_module_function(self):
        """The two build the record independently, so nothing kept them in step.

        ``check_string`` and ``SpoofChecker.check`` each assemble the dict from the
        same flags in their own code, and a check added to one reached the other
        only if somebody remembered. A caller that swaps one for the other should
        not find a field missing.
        """
        for text in ("hello", "pаypal", "i̇"):
            assert SpoofChecker().check(text) == check_string(text), text

    def test_repr(self):
        """Test string representation."""
        checker = SpoofChecker()
        assert "SpoofChecker" in repr(checker)


class TestSpoofCLI:
    """Tests for spoof CLI command."""

    def test_compare_confusable(self):
        """Test compare with confusable strings."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "compare", "paypal", "pаypal"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "confusable" in result.stdout

    def test_compare_not_confusable(self):
        """Test compare with non-confusable strings."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "compare", "hello", "world"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "not confusable" in result.stdout

    def test_skeleton(self):
        """Test skeleton command."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "skeleton", "pаypal"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "paypal" in result.stdout

    def test_check_suspicious(self):
        """Test check command with suspicious string."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "check", "pаypal"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "suspicious" in result.stdout

    def test_check_names_the_issue_it_found(self):
        """Saying "suspicious" and then naming nothing is a report with the finding left out.

        The human rendering listed the checks by hand and omitted the restriction
        level, which is the one that fires for a mixed-script identifier, so the
        commonest suspicious string printed a verdict and no reason for it.
        """
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "check", "pаypal"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "issues: restriction_level" in result.stdout

    def test_check_json_reports_every_named_check(self):
        """``--json`` carries the whole record, so a new check is visible without a CLI edit."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "check", "pаypal", "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        payload = json.loads(result.stdout)
        assert payload == check_string("pаypal")

    def test_check_clean(self):
        """Test check command with clean string."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "check", "hello"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "clean" in result.stdout

    def test_info_json(self):
        """Test info command with JSON output."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "icukit.cli",
                "spoof",
                "info",
                "paypal",
                "pаypal",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"confusable"' in result.stdout

    def test_alias_confusable(self):
        """Test 'confusable' alias."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "confusable", "compare", "a", "а"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_help(self):
        """Test help output."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "spoof", "help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
