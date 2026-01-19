"""
Alphabetic index buckets for sorted lists using ICU's AlphabeticIndex.

Creates locale-aware A-Z style index buckets for organizing sorted lists
like contacts, glossaries, or directory listings.

Example:
    >>> from icukit import create_index_buckets
    >>> buckets = create_index_buckets(["Alice", "Bob", "Carol", "Zebra"], "en_US")
    >>> buckets
    {'A': ['Alice'], 'B': ['Bob'], 'C': ['Carol'], 'Z': ['Zebra']}
"""

from typing import Any

import icu

from .errors import AlphaIndexError

__all__ = [
    "create_index_buckets",
    "get_bucket_labels",
    "get_bucket_for_name",
    "AlphabeticIndex",
]


def create_index_buckets(
    items: list[str],
    locale: str = "en_US",
) -> dict[str, list[str]]:
    """
    Create alphabetic index buckets for a list of items.

    Organizes items into locale-appropriate alphabetic buckets (like A-Z
    in English, or あかさたな in Japanese).

    Args:
        items: List of strings to organize into buckets.
        locale: Locale for bucket labels and sorting rules.

    Returns:
        Dict mapping bucket labels to lists of items in each bucket.

    Example:
        >>> create_index_buckets(["Apple", "Banana", "Bob", "Zebra"], "en_US")
        {'A': ['Apple'], 'B': ['Banana', 'Bob'], 'Z': ['Zebra']}
    """
    try:
        idx = icu.AlphabeticIndex(icu.Locale(locale))

        for item in items:
            idx.addRecord(item, None)

        buckets = {}
        idx.resetBucketIterator()
        while idx.nextBucket():
            if idx.bucketRecordCount > 0:
                label = idx.bucketLabel
                idx.resetRecordIterator()
                records = []
                while idx.nextRecord():
                    records.append(idx.recordName)
                buckets[label] = records

        return buckets
    except icu.ICUError as e:
        raise AlphaIndexError(f"Failed to create index buckets: {e}") from e


def get_bucket_labels(locale: str = "en_US") -> list[str]:
    """
    Get the bucket labels for a locale.

    Returns the alphabetic index labels used for the given locale
    (e.g., A-Z for English, あかさたな for Japanese).

    Args:
        locale: Locale code.

    Returns:
        List of bucket label strings.

    Example:
        >>> get_bucket_labels("en_US")[:5]
        ['A', 'B', 'C', 'D', 'E']
        >>> get_bucket_labels("ja_JP")[:5]
        ['あ', 'か', 'さ', 'た', 'な']
    """
    try:
        idx = icu.AlphabeticIndex(icu.Locale(locale))
        labels = []
        idx.resetBucketIterator()
        while idx.nextBucket():
            label = idx.bucketLabel
            # Skip special buckets (underflow, overflow, inflow)
            if label and label not in ("…", ""):
                labels.append(label)
        return labels
    except icu.ICUError as e:
        raise AlphaIndexError(f"Failed to get bucket labels: {e}") from e


def get_bucket_for_name(name: str, locale: str = "en_US") -> str:
    """
    Get the bucket label for a given name.

    Args:
        name: Name to look up.
        locale: Locale for bucket determination.

    Returns:
        Bucket label for the name.

    Example:
        >>> get_bucket_for_name("Alice", "en_US")
        'A'
        >>> get_bucket_for_name("山田", "ja_JP")
        'や'
    """
    try:
        idx = icu.AlphabeticIndex(icu.Locale(locale))
        idx.addRecord(name, None)

        idx.resetBucketIterator()
        while idx.nextBucket():
            if idx.bucketRecordCount > 0:
                return idx.bucketLabel

        return ""
    except icu.ICUError as e:
        raise AlphaIndexError(f"Failed to get bucket for name: {e}") from e


class AlphabeticIndex:
    """
    Reusable alphabetic index for organizing items into buckets.

    Useful when you need to add items incrementally or access
    bucket information multiple times.

    Example:
        >>> index = AlphabeticIndex("en_US")
        >>> index.add("Alice")
        >>> index.add("Bob")
        >>> index.add("Zebra")
        >>> index.get_buckets()
        {'A': ['Alice'], 'B': ['Bob'], 'Z': ['Zebra']}
    """

    def __init__(self, locale: str = "en_US"):
        """
        Create an alphabetic index for the given locale.

        Args:
            locale: Locale for bucket labels and sorting.
        """
        self.locale = locale
        try:
            self._index = icu.AlphabeticIndex(icu.Locale(locale))
        except icu.ICUError as e:
            raise AlphaIndexError(f"Failed to create index: {e}") from e

    def add(self, name: str, data: Any = None) -> "AlphabeticIndex":
        """
        Add an item to the index.

        Args:
            name: Name/label for the item.
            data: Optional associated data (not returned by get_buckets).

        Returns:
            Self for chaining.
        """
        try:
            self._index.addRecord(name, data)
            return self
        except icu.ICUError as e:
            raise AlphaIndexError(f"Failed to add record: {e}") from e

    def add_many(self, names: list[str]) -> "AlphabeticIndex":
        """
        Add multiple items to the index.

        Args:
            names: List of names to add.

        Returns:
            Self for chaining.
        """
        for name in names:
            self.add(name)
        return self

    def get_buckets(self) -> dict[str, list[str]]:
        """
        Get all non-empty buckets with their items.

        Returns:
            Dict mapping bucket labels to lists of items.
        """
        try:
            buckets = {}
            self._index.resetBucketIterator()
            while self._index.nextBucket():
                if self._index.bucketRecordCount > 0:
                    label = self._index.bucketLabel
                    self._index.resetRecordIterator()
                    records = []
                    while self._index.nextRecord():
                        records.append(self._index.recordName)
                    buckets[label] = records
            return buckets
        except icu.ICUError as e:
            raise AlphaIndexError(f"Failed to get buckets: {e}") from e

    def get_bucket_for(self, name: str) -> str:
        """
        Get the bucket label for a name without adding it.

        Args:
            name: Name to look up.

        Returns:
            Bucket label.
        """
        try:
            bucket_idx = self._index.getBucketIndex(name)
            # Get the label for this bucket index
            self._index.resetBucketIterator()
            for _ in range(bucket_idx + 1):
                self._index.nextBucket()
            return self._index.bucketLabel
        except icu.ICUError as e:
            raise AlphaIndexError(f"Failed to get bucket: {e}") from e

    def get_labels(self) -> list[str]:
        """
        Get all bucket labels for this locale.

        Returns:
            List of bucket label strings.
        """
        try:
            labels = []
            self._index.resetBucketIterator()
            while self._index.nextBucket():
                label = self._index.bucketLabel
                if label and label not in ("…", ""):
                    labels.append(label)
            return labels
        except icu.ICUError as e:
            raise AlphaIndexError(f"Failed to get labels: {e}") from e

    @property
    def bucket_count(self) -> int:
        """Total number of buckets."""
        return self._index.bucketCount

    @property
    def record_count(self) -> int:
        """Total number of records added."""
        return self._index.recordCount

    def clear(self) -> "AlphabeticIndex":
        """
        Clear all records from the index.

        Returns:
            Self for chaining.
        """
        try:
            self._index.clearRecords()
            return self
        except icu.ICUError as e:
            raise AlphaIndexError(f"Failed to clear records: {e}") from e

    def __repr__(self) -> str:
        return f"AlphabeticIndex({self.locale!r}, records={self.record_count})"
