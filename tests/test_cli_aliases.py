"""Tests for command aliases: their declaration, their reach, and their safety.

An alias is a permanent public commitment, and the hazard it carries is silent:
a new alias can capture a prefix that already resolved to a different command,
so an existing invocation keeps working and starts doing something else. The
capture test below is the guard against that, and it must be kept passing by
declining an alias, not by loosening the test.
"""

import argparse
import subprocess
import sys

from icukit.cli.command_trie import CommandTrie, get_all_commands
from icukit.cli.main import create_parser


def _subparsers_action(parser):
    return next(
        (action for action in parser._actions if isinstance(action, argparse._SubParsersAction)),
        None,
    )


def _tries():
    """Yield (scope, trie) for the top-level trie and every subcommand trie."""
    parser = create_parser()
    from icukit.cli.command_trie import _command_trie

    yield "", _command_trie

    action = _subparsers_action(parser)
    seen = set()
    for child in action.choices.values():
        if id(child) in seen:
            continue
        seen.add(id(child))
        trie = getattr(child, "_subcommand_trie", None)
        if trie is not None:
            yield child.prog.split()[-1], trie


def _resolutions(trie):
    """Map every prefix of every registered word to the command it resolves to."""
    words = set()
    for command, aliases in trie.get_all_commands().items():
        words.add(command)
        words.update(aliases)

    resolved = {}
    for word in words:
        for length in range(1, len(word) + 1):
            prefix = word[:length]
            match, _ = trie.find_command(prefix)
            if match is not None:
                resolved[prefix] = match
    return resolved


# Exact aliases that deliberately outrank a prefix of a sibling command. Both
# predate this inventory and both are the intended reading of the short form.
DELIBERATE_EXACT_ALIASES = {
    ("region", "in"): "`region in` reads as containment, not as a prefix of `info`",
    ("unicode", "char"): "`unicode char` reads as a character lookup, which is `info`",
}

# Prefixes two commands already contest, so typing them raises "ambiguous
# command" rather than resolving. Each is a pre-existing consequence of an alias
# that overlaps a sibling; none is silent. A new entry here means a newly added
# alias broke a prefix that used to work, and has to be justified or dropped.
CONTESTED_PREFIXES = {
    ("", "a"),
    ("", "f"),
    ("", "i"),
    ("", "un"),
    ("idna", "t"),
    ("idna", "to"),
    ("idna", "to-"),
    ("locale", "ch"),
    ("locale", "li"),
    ("measure", "com"),
    ("measure", "comp"),
    ("regex", "se"),
    ("unicode", "cate"),
    ("unicode", "categ"),
    ("unicode", "catego"),
    ("unicode", "categor"),
    ("unicode", "cha"),
}


def _prefix_captures():
    """Report every prefix an alias takes away from another command.

    For each registered alias the trie is rebuilt without it. Any prefix that
    resolved to a command in that reduced trie and resolves elsewhere -- or
    nowhere -- in the real one has been captured by that alias. A prefix that
    only becomes usable once the alias is present is a gain, not a capture.
    """
    misrouted, contested = [], []
    for scope, trie in _tries():
        commands = trie.get_all_commands()
        full = _resolutions(trie)
        for owner, aliases in commands.items():
            for alias in aliases:
                reduced = CommandTrie()
                for name, names_aliases in commands.items():
                    kept = [a for a in names_aliases if not (name == owner and a == alias)]
                    reduced.insert(name, kept)
                for prefix, previous in _resolutions(reduced).items():
                    now = full.get(prefix)
                    if now == previous:
                        continue
                    report = (
                        f"{('icukit ' + scope).strip()} {prefix!r}: {previous} -> "
                        f"{now or 'ambiguous'} (alias {alias!r} of {owner!r})"
                    )
                    if now is None:
                        contested.append(((scope, prefix), report))
                    else:
                        misrouted.append(((scope, prefix), report))
    return misrouted, contested


def test_no_alias_silently_reroutes_a_prefix_owned_by_another_command():
    """The hazard an alias carries is that the old invocation keeps working.

    A captured prefix that starts resolving to a different command changes what
    an existing invocation does, with no error to warn anyone. Keep this passing
    by declining the alias, not by extending the exemption list.
    """
    misrouted, _ = _prefix_captures()
    unexpected = [report for key, report in misrouted if key not in DELIBERATE_EXACT_ALIASES]

    assert not unexpected, "aliases reroute prefixes owned by other commands:\n" + "\n".join(
        unexpected
    )


def test_no_alias_newly_breaks_a_prefix_that_used_to_resolve():
    """The quieter half: an alias can leave a working prefix merely ambiguous."""
    _, contested = _prefix_captures()
    unexpected = [report for key, report in contested if key not in CONTESTED_PREFIXES]

    assert not unexpected, "aliases break prefixes that used to resolve:\n" + "\n".join(unexpected)


def test_every_registered_alias_is_an_argparse_choice_for_its_own_command():
    """Aliases are declared once, in the trie, and argparse must learn all of them.

    Without this, `icukit --help` and the generated reference omit every alias
    that was not repeated by hand at the `add_parser` call site.
    """
    parser = create_parser()
    choices = _subparsers_action(parser).choices

    missing = []
    misrouted = []
    for command, aliases in get_all_commands().items():
        for alias in aliases:
            if alias not in choices:
                missing.append(f"{alias!r} (alias of {command!r})")
            elif choices[alias] is not choices[command]:
                misrouted.append(f"{alias!r} does not share a parser with {command!r}")

    assert not missing, "registered aliases argparse never learned: " + ", ".join(missing)
    assert not misrouted, "; ".join(misrouted)


def test_every_argparse_choice_is_a_registered_command_or_one_of_its_aliases():
    """The other direction: a name argparse answers to that the registry never heard of.

    An alias spelled only at the ``add_parser`` call site resolves exactly and no
    other way -- the prefix matcher works off the trie, so no prefix of it
    resolves, and the capture tests above cannot see it either, because they only
    ever look at names the trie knows. That is a public name outside every
    invariant that governs public names, which is how the pair of tests can both
    pass over an alias nobody vetted.
    """
    registered = get_all_commands()
    known = set(registered)
    for aliases in registered.values():
        known.update(aliases)

    parser = create_parser()
    unregistered = sorted(set(_subparsers_action(parser).choices) - known)

    assert not unregistered, (
        "argparse answers to names the command registry never registered, so no "
        f"prefix of them resolves and no alias invariant covers them: {unregistered}"
    )


def test_registered_aliases_appear_in_top_level_help():
    result = subprocess.run(
        [sys.executable, "-m", "icukit.cli", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "break (br, brk)" in result.stdout
    assert "timezone (tz, time)" in result.stdout


def test_timezone_equivalent_is_the_command_and_equiv_still_reaches_it():
    """The canonical name is the full word; the abbreviation stays as an alias."""
    for spelling in ("equivalent", "equiv", "eq", "e"):
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "timezone", spelling, "America/New_York"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{spelling}: {result.stderr}"
        assert "US/Eastern" in result.stdout, spelling


def test_locale_expand_answers_to_maximize():
    """`maximize` is the counterpart a user reaches for after seeing `minimize`."""
    expanded = subprocess.run(
        [sys.executable, "-m", "icukit.cli", "locale", "maximize", "zh"],
        capture_output=True,
        text=True,
    )
    assert expanded.returncode == 0, expanded.stderr
    assert expanded.stdout.strip() == "zh_Hans_CN"
