from __future__ import annotations

from src.core.binary_workbench.editor_consistency.models import ContributionSnapshot


def incremental_offset_values(
    snapshot: ContributionSnapshot,
    first: int,
    maximum_rows: int,
    offset_names: tuple[str, ...],
    offset_bases: dict[str, str],
) -> tuple[tuple[int, dict[str, str]], ...]:
    """Distribute offsets forward from one affected source line.

    Line validity is supplied exclusively by the contribution snapshot. This
    function only carries the previous valid byte position forward and never
    assembles, validates, or interprets source text.
    """

    start = min(max(0, first), snapshot.row_count)
    stop = min(snapshot.row_count, start + max(0, maximum_rows))
    if start >= stop:
        return ()
    values: list[tuple[int, dict[str, str]]] = []
    current_offset = 0
    chunk_first = 0
    for chunk, chunk_sum in zip(snapshot.chunks, snapshot.chunk_sums):
        chunk_stop = chunk_first + len(chunk)
        if chunk_stop <= start:
            current_offset += chunk_sum
            chunk_first = chunk_stop
            continue
        local_start = max(0, start - chunk_first)
        current_offset += sum(chunk[:local_start])
        local_stop = min(len(chunk), stop - chunk_first)
        for local_index in range(local_start, local_stop):
            index = chunk_first + local_index
            size = chunk[local_index]
            offsets = (
                {name: "-" for name in offset_names}
                if size <= 0
                else {
                    name: _formatted_offset(current_offset, name, offset_bases)
                    for name in offset_names
                }
            )
            values.append((index, offsets))
            current_offset += size
        if chunk_stop >= stop:
            break
        chunk_first = chunk_stop
    return tuple(values)


def _formatted_offset(
    file_offset: int,
    name: str,
    offset_bases: dict[str, str],
) -> str:
    """Format File or Reference Offset from the current file position."""

    base = 0 if name == "File" else int(offset_bases.get(name, "0x0"), 0)
    return f"0x{file_offset + base:08X}"
