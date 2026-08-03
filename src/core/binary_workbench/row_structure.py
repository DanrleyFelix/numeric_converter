from src.core.binary_workbench.mips_r3000a.comments import strip_comment
from src.core.binary_workbench.mips_r3000a.source_line_rows import split_label
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_FILE_OFFSET_COLUMN as FILE_OFFSET,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def valid_offset_end(rows: list[BinaryWorkbenchRowDTO]) -> int:
    """Return the byte end immediately after the last valid file offset."""

    for row in reversed(rows):
        value = row.offsets.get(FILE_OFFSET)
        if value in {None, "-"}:
            continue
        try:
            return int(value, 0) + ROW_BYTES
        except ValueError:
            continue
    return 0


def structural_offset_delta(
    previous: list[BinaryWorkbenchRowDTO],
    current: list[BinaryWorkbenchRowDTO],
) -> int:
    """Return the final-offset delta produced by a structural row change."""

    return valid_offset_end(current) - valid_offset_end(previous)


def file_offset_layout_changed(
    previous: list[BinaryWorkbenchRowDTO],
    current: list[BinaryWorkbenchRowDTO],
) -> bool:
    """Return whether any source row moved into or out of a file offset."""

    return len(previous) != len(current) or any(
        before.offsets.get(FILE_OFFSET) != after.offsets.get(FILE_OFFSET)
        for before, after in zip(previous, current)
    )


def first_valid_label_offset(
    rows: list[BinaryWorkbenchRowDTO],
    label: str,
) -> int | None:
    """Resolve one label to the first valid offset at or after its row."""

    target = label.lower()
    matched = False
    for row in rows:
        if not matched:
            current, _ = split_label(strip_comment(row.instruction).strip())
            matched = current.lower() == target
        if not matched:
            continue
        value = row.offsets.get(FILE_OFFSET)
        if value in {None, "-"}:
            continue
        try:
            return int(value, 0)
        except ValueError:
            continue
    return None
