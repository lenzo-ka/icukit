"""Unicode script detection and properties.

Detect the writing system (script) of text and query script properties.
Scripts include Latin, Greek, Cyrillic, Han, Arabic, Hebrew, and many more.

Key Features:
    * Detect script of text or individual characters
    * Check if script has case distinctions (upper/lowercase)
    * Check if script is right-to-left
    * List all available scripts

Example:
    Detect script of text::

        >>> from icukit import detect_script, is_rtl
        >>>
        >>> detect_script('Hello')
        'Latin'
        >>> detect_script('Ελληνικά')
        'Greek'
        >>> detect_script('你好')
        'Han'
        >>>
        >>> is_rtl('Hello')
        False
        >>> is_rtl('مرحبا')
        True

    Query script properties::

        >>> from icukit import get_script_info, list_scripts
        >>>
        >>> info = get_script_info('Greek')
        >>> info['is_cased']
        True
        >>> info['is_rtl']
        False
        >>>
        >>> scripts = list_scripts()
        >>> len(scripts)
        160
"""

from typing import Any, Dict, Iterator, List, Optional

import icu

from .errors import ScriptError

# PyICU doesn't expose USCRIPT_CODE_LIMIT, so we iterate until we hit
# an invalid script code. This upper bound is safe for future Unicode versions.
_MAX_SCRIPT_CODE = 500


def _iter_scripts() -> Iterator[icu.Script]:
    """Iterate over all valid ICU script objects."""
    for i in range(_MAX_SCRIPT_CODE):
        try:
            script = icu.Script(i)
            name = script.getName()
            if name and name != "Unknown":
                yield script
        except (ValueError, icu.ICUError):
            break


def list_scripts() -> List[str]:
    """List all available Unicode scripts.

    Returns:
        List of script names sorted alphabetically.

    Example:
        >>> scripts = list_scripts()
        >>> 'Latin' in scripts
        True
        >>> 'Greek' in scripts
        True
    """
    return sorted(script.getName() for script in _iter_scripts())


def list_scripts_info() -> List[Dict[str, Any]]:
    """List all scripts with their properties.

    Returns:
        List of dicts with script info: code, name, is_cased, is_rtl.

    Example:
        >>> scripts = list_scripts_info()
        >>> greek = next(s for s in scripts if s['name'] == 'Greek')
        >>> greek['is_cased']
        True
    """
    results = [
        {
            "code": script.getShortName(),
            "name": script.getName(),
            "is_cased": script.isCased(),
            "is_rtl": script.isRightToLeft(),
        }
        for script in _iter_scripts()
    ]
    return sorted(results, key=lambda x: x["name"])


def get_script_info(script: str, extended: bool = False) -> Optional[Dict[str, Any]]:
    """Get information about a script.

    Args:
        script: Script name (e.g., 'Greek', 'Latin') or code (e.g., 'Grek', 'Latn').
        extended: Include extended attributes (sample_char).

    Returns:
        Dict with script info, or None if not found.

    Raises:
        ScriptError: If script name/code is invalid.

    Example:
        >>> info = get_script_info('Greek')
        >>> info['code']
        'Grek'
        >>> info['is_cased']
        True
        >>> info = get_script_info('Arabic', extended=True)
        >>> info['extended']['sample_char']
        'ب'
    """
    try:
        codes = icu.Script.getCode(script)
        if not codes:
            return None
        script_obj = icu.Script(codes[0])
        info = {
            "code": script_obj.getShortName(),
            "name": script_obj.getName(),
            "is_cased": script_obj.isCased(),
            "is_rtl": script_obj.isRightToLeft(),
        }
        if extended:
            info["extended"] = {
                "sample_char": script_obj.getSampleString() or None,
            }
        return info
    except icu.ICUError as e:
        raise ScriptError(f"Invalid script: {script}") from e


def detect_script(text: str) -> str:
    """Detect the primary script of text.

    Analyzes the first character to determine the script. For mixed-script
    text, use detect_scripts() to get all scripts present.

    Args:
        text: Text to analyze.

    Returns:
        Script name (e.g., 'Latin', 'Greek', 'Han').

    Example:
        >>> detect_script('Hello')
        'Latin'
        >>> detect_script('Ελληνικά')
        'Greek'
        >>> detect_script('你好世界')
        'Han'
        >>> detect_script('مرحبا')
        'Arabic'
    """
    if not text:
        return "Unknown"
    return icu.Script.getScript(text[0]).getName()


def detect_scripts(text: str) -> List[str]:
    """Detect all scripts present in text.

    Args:
        text: Text to analyze.

    Returns:
        List of unique script names found, in order of first occurrence.

    Example:
        >>> detect_scripts('Hello Ελληνικά')
        ['Latin', 'Common', 'Greek']
        >>> detect_scripts('abc123')
        ['Latin', 'Common']
    """
    if not text:
        return []
    seen = set()
    scripts = []
    for char in text:
        script = icu.Script.getScript(char).getName()
        if script not in seen:
            seen.add(script)
            scripts.append(script)
    return scripts


def is_cased(script: str) -> bool:
    """Check if a script has case distinctions.

    Cased scripts have uppercase and lowercase letter variants.
    Examples: Latin, Greek, Cyrillic are cased. Han, Arabic, Hebrew are not.

    Args:
        script: Script name or code.

    Returns:
        True if script has case distinctions.

    Raises:
        ScriptError: If script is invalid.

    Example:
        >>> is_cased('Latin')
        True
        >>> is_cased('Greek')
        True
        >>> is_cased('Han')
        False
        >>> is_cased('Arabic')
        False
    """
    info = get_script_info(script)
    if info is None:
        raise ScriptError(f"Unknown script: {script}")
    return info["is_cased"]


def is_rtl(text: str) -> bool:
    """Check if text is in a right-to-left script.

    RTL scripts include Arabic, Hebrew, Syriac, etc.

    Args:
        text: Text to check.

    Returns:
        True if the primary script is right-to-left.

    Example:
        >>> is_rtl('Hello')
        False
        >>> is_rtl('مرحبا')
        True
        >>> is_rtl('שלום')
        True
    """
    if not text:
        return False
    return icu.Script.getScript(text[0]).isRightToLeft()


def get_char_script(char: str) -> str:
    """Get the script of a single character.

    Args:
        char: A single character.

    Returns:
        Script name.

    Raises:
        ValueError: If input is not a single character.

    Example:
        >>> get_char_script('α')
        'Greek'
        >>> get_char_script('A')
        'Latin'
        >>> get_char_script('你')
        'Han'
    """
    if len(char) != 1:
        raise ValueError("Input must be a single character")
    return icu.Script.getScript(char).getName()
