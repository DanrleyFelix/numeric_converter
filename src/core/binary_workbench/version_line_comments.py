from __future__ import annotations

from src.modules.dtos import BinaryWorkbenchRowDTO

FILE_OFFSET = "File"
EMPTY_OFFSET = "-"
ROW_BYTES = 4


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
