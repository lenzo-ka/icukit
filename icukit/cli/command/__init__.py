"""CLI commands."""

from .alpha_index import AlphaIndexCommand
from .bidi import BidiCommand
from .breaker import BreakerCommand
from .calendar import CalendarCommand
from .collator import CollatorCommand
from .compact import CompactCommand
from .datetime import DateTimeCommand
from .discover import DiscoverCommand
from .displayname import DisplayNameCommand
from .duration import DurationCommand
from .help_cmd import add_subparser as add_help_subparser
from .idna import IDNACommand
from .listfmt import ListFmtCommand
from .locale import LocaleCommand
from .measure import MeasureCommand
from .message import MessageCommand
from .parse import ParseCommand
from .plural import PluralCommand
from .regex import RegexCommand
from .region import RegionCommand
from .script import ScriptCommand
from .search import SearchCommand
from .sort import SortCommand
from .spoof import SpoofCommand
from .timezone import TimezoneCommand
from .transliterate import TransliterateCommand
from .unicode import UnicodeCommand

__all__ = [
    "AlphaIndexCommand",
    "BidiCommand",
    "BreakerCommand",
    "CalendarCommand",
    "CollatorCommand",
    "CompactCommand",
    "DateTimeCommand",
    "DiscoverCommand",
    "DisplayNameCommand",
    "DurationCommand",
    "IDNACommand",
    "ListFmtCommand",
    "LocaleCommand",
    "MeasureCommand",
    "MessageCommand",
    "ParseCommand",
    "PluralCommand",
    "RegexCommand",
    "RegionCommand",
    "ScriptCommand",
    "SearchCommand",
    "SortCommand",
    "SpoofCommand",
    "TimezoneCommand",
    "TransliterateCommand",
    "UnicodeCommand",
    "add_help_subparser",
]
