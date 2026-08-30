"""Invariants over the whole command registry, quantified rather than enumerated.

A test that lists today's commands proves only that today's commands behave. The
next command added is outside its reach, so the claim the test was written to
defend stops being guarded without anything going red -- the test keeps passing
and simply stops being about the CLI. Two claims in the changelog were in exactly
that position: that every subcommand of the four commands made uniform takes
``--json``, and that every registered alias reaches argparse. Both were true and
neither was enforced.

Everything here walks the parser tree instead of naming its members, so a command
added tomorrow falls inside the invariant the moment it is registered, and the
only way past an invariant is to record the exception with a reason.
"""

import argparse

import pytest

from icukit.cli.command_trie import get_all_commands
from icukit.cli.main import create_parser

# The commands the changelog describes as uniform in their --json coverage. Named
# here because uniformity is a claim about these four and not about the CLI as a
# whole; test_uniform_json_commands_are_registered keeps the names from decaying
# into a set that quantifies over nothing.
UNIFORM_JSON_COMMANDS = frozenset({"collate", "datetime", "idna", "measure"})

# Every leaf in the CLI that does not take --json, grouped by why. The invariant
# compares this against the registry in both directions: a new leaf without
# --json fails until it is either given one or recorded here with a reason, and a
# leaf that gains --json fails until its entry is removed.
#
# A ``help`` leaf is exempt by construction rather than by entry.
# ``create_subcommand_parser`` adds one to every command with subcommands, and it
# prints help text rather than producing a record, so twenty-five identical rows
# would say nothing that this sentence does not.
LEAVES_WITHOUT_JSON = {
    "reports its answer through the exit status, which a record would only restate": frozenset(
        {
            ("bidi", "check"),
            ("locale", "compare"),
            ("locale", "validate"),
            ("regex", "match"),
            ("regex", "search"),
            ("script", "rtl"),
            ("search", "contains"),
            ("spoof", "compare"),
            ("unicode", "check"),
        }
    ),
    "emits one value on one line, and wrapping a scalar in JSON carries nothing more": frozenset(
        {
            ("alpha-index", "bucket"),
            ("bidi", "strip"),
            ("compact", ""),
            ("displayname", "currency"),
            ("displayname", "language"),
            ("displayname", "locale"),
            ("displayname", "region"),
            ("displayname", "script"),
            ("displayname", "symbol"),
            ("duration", "format"),
            ("duration", "iso"),
            ("listfmt", ""),
            ("locale", "canonicalize"),
            ("locale", "compact"),
            ("locale", "expand"),
            ("locale", "format"),
            ("locale", "minimize"),
            ("locale", "name"),
            ("locale", "ordinal"),
            ("locale", "spellout"),
            ("message", "format"),
            ("parse", "number"),
            ("parse", "percent"),
            ("plural", "ordinal"),
            ("plural", "select"),
            ("search", "count"),
            ("search", "replace"),
            ("spoof", "skeleton"),
            ("unicode", "encode"),
        }
    ),
    "emits a collection as plain lines and has no --json yet: a gap, not a decision": frozenset(
        {
            ("alpha-index", "labels"),
            ("locale", "sort"),
            ("message", "examples"),
            ("sort", ""),
        }
    ),
}


def _subparsers_action(parser):
    return next(
        (action for action in parser._actions if isinstance(action, argparse._SubParsersAction)),
        None,
    )


def _distinct_choices(action):
    """The parsers behind a subparsers action, once each.

    Aliases share a parser object with the command they alias, so iterating the
    choices mapping would visit the same command several times under different
    names. Each parser reports its own canonical name in ``prog``.
    """
    seen = {}
    for parser in action.choices.values():
        seen.setdefault(id(parser), parser)
    return list(seen.values())


def commands():
    """Yield ``(name, parser)`` for every registered top-level command."""
    action = _subparsers_action(create_parser())
    for parser in _distinct_choices(action):
        yield parser.prog.split()[-1], parser


def leaves():
    """Yield ``(command, leaf, parser)`` for every leaf the command line can reach.

    A command with no subcommands is its own leaf and reports an empty leaf name.
    """
    for name, parser in commands():
        action = _subparsers_action(parser)
        if action is None:
            yield name, "", parser
            continue
        for leaf in _distinct_choices(action):
            yield name, leaf.prog.split()[-1], leaf


def takes_json(parser) -> bool:
    return any("--json" in action.option_strings for action in parser._actions)


def is_a_help_leaf(command: str, leaf: str) -> bool:
    """Whether this leaf exists to print help rather than to produce a record."""
    return leaf == "help" or (command, leaf) == ("help", "")


def test_uniform_json_commands_are_registered():
    """The named set has to name something, or the invariant below quantifies over nothing.

    Renaming a command while leaving this set behind is the silent way to switch
    off a uniformity guard: the set keeps its old spelling, matches no command,
    and the guard passes over an empty collection.
    """
    registered = {name for name, _ in commands()}
    assert UNIFORM_JSON_COMMANDS <= registered, sorted(UNIFORM_JSON_COMMANDS - registered)


@pytest.mark.parametrize("command", sorted(UNIFORM_JSON_COMMANDS))
def test_every_leaf_of_a_uniform_json_command_takes_json(command):
    """Uniformity is a property of the whole family, so it is checked over the whole family.

    Adding a subcommand to one of these four without ``--json`` breaks the claim
    the changelog makes about it, and this is what says so.
    """
    without = sorted(
        leaf
        for name, leaf, parser in leaves()
        if name == command and not is_a_help_leaf(name, leaf) and not takes_json(parser)
    )
    assert not without, f"{command} claims uniform --json but these leaves lack it: {without}"


def test_the_leaves_without_json_are_exactly_the_ones_recorded():
    """The rest of the CLI is held by a ratchet, not left unmeasured.

    The equality is deliberate. A new leaf without ``--json`` fails until somebody
    either gives it one or writes down why it has none, and a leaf that gains
    ``--json`` fails until its entry goes, so the record cannot quietly outlive
    the reason for it.
    """
    recorded = {leaf for group in LEAVES_WITHOUT_JSON.values() for leaf in group}
    actual = {
        (name, leaf)
        for name, leaf, parser in leaves()
        if not is_a_help_leaf(name, leaf) and not takes_json(parser)
    }
    assert actual == recorded, (
        f"leaves without --json that are not recorded: {sorted(actual - recorded)}; "
        f"recorded leaves that now take --json or no longer exist: {sorted(recorded - actual)}"
    )


def test_no_leaf_is_recorded_under_two_reasons():
    """One leaf, one reason: a leaf listed twice has an explanation nobody can rely on."""
    counted = [leaf for group in LEAVES_WITHOUT_JSON.values() for leaf in group]
    duplicated = sorted({leaf for leaf in counted if counted.count(leaf) > 1})
    assert not duplicated, duplicated


def test_every_command_registers_itself_with_the_prefix_trie():
    """Prefix resolution runs off the trie, so a command absent from it is unreachable by prefix.

    ``create_parser`` pairs a ``register_command`` call with each
    ``add_subparser``; nothing enforced the pairing, so a command added with the
    second and not the first would answer to its full name alone, and only to it.
    """
    registered = set(get_all_commands())
    missing = sorted({name for name, _ in commands()} - registered)
    assert not missing, f"commands argparse knows that the prefix trie does not: {missing}"
