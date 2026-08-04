from __future__ import annotations

from bisect import bisect_right

from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken
from src.core.binary_workbench.editor_consistency.constants import (
    CONTRIBUTION_CHUNK_SIZE,
    OFFSET_BATCH_SIZE,
    VIEWPORT_MARGIN_LINES,
)
from src.core.binary_workbench.editor_consistency.models import (
    ContributionSnapshot,
    DirtyRange,
    EditorOwner,
    OffsetDistributionBatch,
)


class LineContributionIndex:
    """Maintain emitted byte sizes in immutable, shareable chunks."""

    def __init__(self, sizes: list[int] | tuple[int, ...] = ()) -> None:
        self._chunks = _chunked(tuple(max(0, value) for value in sizes))

    def splice(self, first: int, removed: int, inserted: list[int]) -> None:
        """Replace one contiguous contribution range."""

        count = sum(len(chunk) for chunk in self._chunks)
        start = min(max(0, first), count)
        end = min(count, start + max(0, removed))
        start_chunk, start_local = _chunk_position(self._chunks, start)
        end_chunk, end_local = _chunk_position(self._chunks, end)

        before = self._chunks[:start_chunk]
        prefix = self._chunks[start_chunk][:start_local] if start_chunk < len(self._chunks) else ()
        if end_chunk < len(self._chunks):
            suffix = self._chunks[end_chunk][end_local:]
            after = self._chunks[end_chunk + 1 :]
        else:
            suffix = ()
            after = ()
        replacement = (*prefix, *(max(0, value) for value in inserted), *suffix)
        self._chunks = (*before, *_chunked(replacement), *after)

    def prefix_bytes(self, line: int) -> int:
        """Return emitted bytes preceding the requested source line."""

        remaining = min(max(0, line), sum(len(chunk) for chunk in self._chunks))
        total = 0
        for chunk in self._chunks:
            if remaining <= 0:
                break
            used = min(remaining, len(chunk))
            total += sum(chunk[:used])
            remaining -= used
        return total

    def snapshot(self) -> ContributionSnapshot:
        """Return chunked immutable sizes without copying source text."""

        chunks = self._chunks
        return ContributionSnapshot(
            chunks,
            tuple(sum(chunk) for chunk in chunks),
            sum(len(chunk) for chunk in chunks),
        )


def build_offset_batches(
    snapshot: ContributionSnapshot,
    owner: EditorOwner,
    structural_revision: int,
    generation: int,
    offset_names: tuple[str, ...],
    offset_bases: dict[str, str],
    dirty_ranges: tuple[DirtyRange, ...],
    dirty_from_line: int | None,
    viewport: DirtyRange,
    token: CancellationToken,
) -> tuple[OffsetDistributionBatch, ...]:
    """Build prioritized offset batches from emitted-size metadata."""

    return tuple(
        iter_offset_batches(
            snapshot,
            owner,
            structural_revision,
            generation,
            offset_names,
            offset_bases,
            dirty_ranges,
            dirty_from_line,
            viewport,
            token,
        )
    )


def iter_offset_batches(
    snapshot: ContributionSnapshot,
    owner: EditorOwner,
    structural_revision: int,
    generation: int,
    offset_names: tuple[str, ...],
    offset_bases: dict[str, str],
    dirty_ranges: tuple[DirtyRange, ...],
    dirty_from_line: int | None,
    viewport: DirtyRange,
    token: CancellationToken,
):
    """Yield prioritized batches so the viewport can commit progressively."""

    chunk_starts = _chunk_starts(snapshot.chunks)
    byte_starts = _byte_starts(snapshot.chunk_sums)
    order = _priority_order(snapshot.row_count, dirty_ranges, dirty_from_line, viewport)
    for start in range(0, len(order), OFFSET_BATCH_SIZE):
        if token.is_cancelled():
            return
        indices = order[start : start + OFFSET_BATCH_SIZE]
        values = tuple(
            (
                index,
                _offsets_for(
                    index,
                    snapshot,
                    chunk_starts,
                    byte_starts,
                    offset_names,
                    offset_bases,
                ),
            )
            for index in indices
        )
        if values:
            yield OffsetDistributionBatch(
                owner,
                structural_revision,
                generation,
                min(indices),
                max(indices),
                values,
            )


def _priority_order(
    count: int,
    dirty_ranges: tuple[DirtyRange, ...],
    dirty_from_line: int | None,
    viewport: DirtyRange,
) -> list[int]:
    seen: set[int] = set()
    output: list[int] = []
    ranges = [
        *dirty_ranges,
        viewport,
        DirtyRange(viewport.first - VIEWPORT_MARGIN_LINES, viewport.last + VIEWPORT_MARGIN_LINES),
        DirtyRange(0 if dirty_from_line is None else dirty_from_line, count - 1),
    ]
    for item in ranges:
        for index in range(max(0, item.first), min(count, item.last + 1)):
            if index not in seen:
                seen.add(index)
                output.append(index)
    return output


def _offsets_for(
    index: int,
    snapshot: ContributionSnapshot,
    chunk_starts: tuple[int, ...],
    byte_starts: tuple[int, ...],
    names: tuple[str, ...],
    bases: dict[str, str],
) -> dict[str, str]:
    chunk_index = max(0, bisect_right(chunk_starts, index) - 1)
    local = index - chunk_starts[chunk_index]
    chunk = snapshot.chunks[chunk_index]
    if chunk[local] <= 0:
        return {name: "-" for name in names}
    offset = byte_starts[chunk_index] + sum(chunk[:local])
    return {
        name: f"0x{offset + (0 if name == 'File' else int(bases.get(name, '0x0'), 0)):08X}"
        for name in names
    }


def _chunked(values: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        values[start : start + CONTRIBUTION_CHUNK_SIZE]
        for start in range(0, len(values), CONTRIBUTION_CHUNK_SIZE)
    )


def _chunk_position(
    chunks: tuple[tuple[int, ...], ...],
    position: int,
) -> tuple[int, int]:
    remaining = position
    for index, chunk in enumerate(chunks):
        if remaining < len(chunk):
            return index, remaining
        if remaining == len(chunk):
            return index + 1, 0
        remaining -= len(chunk)
    return len(chunks), 0


def _chunk_starts(chunks: tuple[tuple[int, ...], ...]) -> tuple[int, ...]:
    starts: list[int] = []
    line = 0
    for chunk in chunks:
        starts.append(line)
        line += len(chunk)
    return tuple(starts)


def _byte_starts(chunk_sums: tuple[int, ...]) -> tuple[int, ...]:
    starts: list[int] = []
    offset = 0
    for value in chunk_sums:
        starts.append(offset)
        offset += value
    return tuple(starts)
