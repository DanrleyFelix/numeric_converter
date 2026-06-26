from __future__ import annotations

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_EMPTY_OFFSET as EMPTY_OFFSET,
    BINARY_WORKBENCH_FILE_OFFSET_COLUMN as FILE_OFFSET,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def apply_line_comments(
    rows: list[BinaryWorkbenchRowDTO],
    instructions: dict[int, str],
    offset_names: list[str],
) -> list[BinaryWorkbenchRowDTO]:
    updated = list(rows)
    base = line_base(rows)
    for line, instruction in sorted(instructions.items()):
        index = line - base
        if 0 <= index <= len(updated):
            updated.insert(index, comment_row(instruction, offset_names))
    return updated


def comment_row(instruction: str, offset_names: list[str]) -> BinaryWorkbenchRowDTO:
    return BinaryWorkbenchRowDTO(
        offsets={name: EMPTY_OFFSET for name in offset_names},
        instruction=instruction,
        bytes_text="",
    )


def line_base(rows: list[BinaryWorkbenchRowDTO]) -> int:
    for index, row in enumerate(rows):
        try:
            return (int(row.offsets.get(FILE_OFFSET, EMPTY_OFFSET), 16) // ROW_BYTES) - index
        except ValueError:
            continue
    return 0
