from __future__ import annotations

from typing import Sequence

from ..policy import ByteEditViolation, ByteRowAccess, ByteRowPolicy

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def byte_edit_violation(
    previous_lines: Sequence[str],
    current_lines: Sequence[str],
    policies: Sequence[ByteRowPolicy],
    edit_index: int | None = None,
) -> ByteEditViolation:
    """Validate one complete Bytes mutation against its Assembly row policies."""

    before = tuple(_canonical_line(line) for line in previous_lines)
    after = tuple(_canonical_line(line) for line in current_lines)
    if len(after) < len(before):
        removed = removed_source_indices(before, after, edit_index)
        if not removed or any(
            not _policy_at(policies, index).removable_from_bytes
            for index in removed
        ):
            return ByteEditViolation.ROW_REMOVAL
    aligned = aligned_source_indices(before, after, edit_index)
    for current_index, source_index in enumerate(aligned):
        if source_index is None:
            continue
        if (
            before[source_index] != after[current_index]
            and _policy_at(policies, source_index).access
            is ByteRowAccess.ASSEMBLY_ONLY
        ):
            return ByteEditViolation.ASSEMBLY_ONLY
    return ByteEditViolation.NONE


def removed_source_indices(
    previous_lines: Sequence[str],
    current_lines: Sequence[str],
    edit_index: int | None = None,
) -> tuple[int, ...]:
    """Return rows from a pure deletion, rejecting simultaneous replacements."""

    if len(current_lines) >= len(previous_lines):
        return ()
    before = tuple(_canonical_line(line) for line in previous_lines)
    after = tuple(_canonical_line(line) for line in current_lines)
    removed_count = len(before) - len(after)
    if edit_index is not None:
        start = min(max(0, edit_index), len(before) - removed_count)
        if before[:start] + before[start + removed_count :] == after:
            return tuple(range(start, start + removed_count))
    current_index = 0
    removed: list[int] = []
    for source_index, source_line in enumerate(before):
        if current_index < len(after) and source_line == after[current_index]:
            current_index += 1
        else:
            removed.append(source_index)
    return tuple(removed) if current_index == len(after) else ()


def byte_lines_ready_for_commit(
    previous_lines: Sequence[str],
    current_lines: Sequence[str],
    row_bytes: int,
    edit_index: int | None = None,
) -> bool:
    """Return whether every changed Bytes row is complete and atomic."""

    expected_digits = row_bytes * 2
    aligned = aligned_source_indices(previous_lines, current_lines, edit_index)
    for index, line in enumerate(current_lines):
        source_index = aligned[index]
        previous = (
            previous_lines[source_index]
            if source_index is not None and source_index < len(previous_lines)
            else None
        )
        if previous is not None and _canonical_line(previous) == _canonical_line(line):
            continue
        raw = "".join(character for character in line if not character.isspace())
        if edit_index is not None and source_index is None and not raw:
            continue
        if len(raw) != expected_digits or any(character not in _HEX_DIGITS for character in raw):
            return False
    return True


def aligned_source_indices(
    previous_lines: Sequence[str],
    current_lines: Sequence[str],
    edit_index: int | None = None,
) -> tuple[int | None, ...]:
    """Map one aggregated Bytes splice back to stable source-row identities."""

    before = tuple(_canonical_line(line) for line in previous_lines)
    after = tuple(_canonical_line(line) for line in current_lines)
    delta = len(after) - len(before)
    if edit_index is not None and delta:
        boundary = min(max(0, edit_index), len(before))
        if delta > 0:
            return tuple(
                index
                if index < boundary
                else None
                if index < boundary + delta
                else index - delta
                for index in range(len(after))
            )
        removed = -delta
        boundary = min(boundary, max(0, len(before) - removed))
        return tuple(
            index if index < boundary else index + removed
            for index in range(len(after))
        )
    prefix = _common_prefix(before, after)
    suffix = _common_suffix(before[prefix:], after[prefix:])
    aligned: list[int | None] = [None] * len(after)
    for index in range(prefix):
        aligned[index] = index
    for offset in range(suffix):
        aligned[len(after) - suffix + offset] = len(before) - suffix + offset
    old_middle = len(before) - prefix - suffix
    new_middle = len(after) - prefix - suffix
    for offset in range(min(old_middle, new_middle)):
        aligned[prefix + offset] = prefix + offset
    return tuple(aligned)


def _canonical_line(line: str) -> str:
    return "".join(line.split()).upper()


def _common_prefix(first: Sequence[str], second: Sequence[str]) -> int:
    index = 0
    while index < min(len(first), len(second)) and first[index] == second[index]:
        index += 1
    return index


def _common_suffix(first: Sequence[str], second: Sequence[str]) -> int:
    index = 0
    while index < min(len(first), len(second)) and first[-index - 1] == second[-index - 1]:
        index += 1
    return index


def _policy_at(policies: Sequence[ByteRowPolicy], index: int) -> ByteRowPolicy:
    return policies[index] if 0 <= index < len(policies) else ByteRowPolicy(ByteRowAccess.EDITABLE)
