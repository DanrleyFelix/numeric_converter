from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Iterator, Sequence


class PrefixQuery(Sequence[str]):
    """Zero-copy view over a contiguous prefix range in a sorted catalog."""

    def __init__(
        self,
        values: tuple[str, ...],
        start: int,
        stop: int,
        exact_index: int | None = None,
    ) -> None:
        self._values = values
        self._start = start
        self._stop = stop
        self._exact_index = exact_index

    def __len__(self) -> int:
        length = self._stop - self._start
        return length - int(self._exact_index is not None)

    def __getitem__(self, index: int | slice) -> str | tuple[str, ...]:
        if isinstance(index, slice):
            return tuple(self)[index]
        length = len(self)
        if index < 0:
            index += length
        if not 0 <= index < length:
            raise IndexError(index)
        source_index = self._start + index
        if self._exact_index is not None and source_index >= self._exact_index:
            source_index += 1
        return self._values[source_index]

    def __iter__(self) -> Iterator[str]:
        for index in range(len(self)):
            yield self[index]


class PrefixCatalog:
    """Immutable case-insensitive catalog supporting O(log n) prefix lookup."""

    def __init__(self, values: Sequence[str]) -> None:
        ordered = tuple(sorted(values, key=str.casefold))
        self._values = ordered
        self._keys = tuple(value.casefold() for value in ordered)

    @property
    def values(self) -> tuple[str, ...]:
        return self._values

    def query(self, prefix: str) -> PrefixQuery:
        normalized = prefix.casefold()
        if not normalized:
            return PrefixQuery(self._values, 0, 0)
        start = bisect_left(self._keys, normalized)
        stop = bisect_right(self._keys, normalized + "\U0010ffff")
        exact = start if start < stop and self._keys[start] == normalized else None
        return PrefixQuery(self._values, start, stop, exact)
