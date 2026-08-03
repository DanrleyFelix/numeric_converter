from __future__ import annotations

from dataclasses import dataclass

from src.core.binary_workbench.mips_r3000a.source_line_rows import (
    build_source_line_rows,
    labels_from_source_rows,
)
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_ASSEMBLY_REFRESH_WINDOW_BYTES,
    BINARY_WORKBENCH_ROW_BYTES,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.modules.contracts import CPUArchCodec


@dataclass(frozen=True)
class SourceRefreshWindow:
    """A bounded source-row window backed by executable byte positions."""

    first_row: int
    last_row: int
    first_byte: int
    last_byte: int


def source_refresh_window(
    rows: list[BinaryWorkbenchRowDTO],
    anchor_row: int,
    byte_limit: int = BINARY_WORKBENCH_ASSEMBLY_REFRESH_WINDOW_BYTES,
) -> SourceRefreshWindow:
    """Center a byte-bounded refresh window around one visible source row."""

    executable_rows = [index for index, row in enumerate(rows) if row.bytes_text]
    total_bytes = len(executable_rows) * BINARY_WORKBENCH_ROW_BYTES
    if not executable_rows:
        return SourceRefreshWindow(0, len(rows), 0, 0)
    before_anchor = sum(index < anchor_row for index in executable_rows)
    anchor_byte = before_anchor * BINARY_WORKBENCH_ROW_BYTES
    first_byte = max(0, anchor_byte - (byte_limit // 2))
    first_byte = min(first_byte, max(0, total_bytes - byte_limit))
    first_ordinal = first_byte // BINARY_WORKBENCH_ROW_BYTES
    last_ordinal = min(
        len(executable_rows),
        first_ordinal + (byte_limit // BINARY_WORKBENCH_ROW_BYTES),
    )
    first_row = executable_rows[first_ordinal]
    while first_row > 0 and not rows[first_row - 1].bytes_text:
        first_row -= 1
    last_row = executable_rows[last_ordinal - 1] + 1
    return SourceRefreshWindow(
        first_row,
        last_row,
        first_ordinal * BINARY_WORKBENCH_ROW_BYTES,
        last_ordinal * BINARY_WORKBENCH_ROW_BYTES,
    )


def build_source_refresh_rows(
    lines: list[str],
    offset_names: list[str],
    offset_bases: dict[str, str],
    codec: CPUArchCodec,
    start_offset: int,
    outside_labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> tuple[list[BinaryWorkbenchRowDTO] | None, dict[str, str]]:
    """Resolve labels and assemble only one bounded source region."""

    labels = dict(outside_labels)
    rows = None
    for _ in range(3):
        rows = build_source_line_rows(
            lines,
            offset_names,
            offset_bases,
            codec,
            start_offset,
            labels,
            variables,
            equates,
            False,
        )
        if rows is None:
            return None, labels
        local_labels = labels_from_source_rows(
            rows,
            start_offset,
            BINARY_WORKBENCH_ROW_BYTES,
        )
        updated = {**outside_labels, **local_labels}
        if updated == labels:
            break
        labels = updated
    return rows, labels
