from __future__ import annotations

from src.modules.dtos import BinaryWorkbenchRowDTO

LABEL_SEPARATOR = ":"
DEFAULT_FILE_OFFSET = "0x00000000"


def apply_instruction_overlays(
    rows: list[BinaryWorkbenchRowDTO],
    overlays: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    return [
        BinaryWorkbenchRowDTO(
            offsets=row.offsets,
            instruction=overlays.get(file_offset(row), row.instruction),
            bytes_text=row.bytes_text,
        )
        for row in rows
    ]


def update_instruction_overlays(
    overlays: dict[str, str],
    rows: list[BinaryWorkbenchRowDTO],
    previous_rows: list[BinaryWorkbenchRowDTO],
) -> dict[str, str]:
    updated = dict(overlays)
    previous = {file_offset(row): row.instruction for row in previous_rows}
    for row in rows:
        offset = file_offset(row)
        if previous.get(offset) == row.instruction:
            continue
        if row.instruction.strip():
            updated[offset] = row.instruction
        else:
            updated.pop(offset, None)
    return updated


def labels_from_rows(rows: list[BinaryWorkbenchRowDTO]) -> dict[str, str]:
    return {
        label: file_offset(row)
        for row in rows
        if (label := label_from_instruction(row.instruction))
    }


def labels_from_lines_at_rows(
    lines: list[str],
    rows: list[BinaryWorkbenchRowDTO],
) -> dict[str, str]:
    return {
        label: file_offset(row)
        for line, row in zip(lines, rows)
        if (label := label_from_instruction(line))
    }


def labels_from_overlays(overlays: dict[str, str]) -> dict[str, str]:
    return {
        label: offset
        for offset, instruction in overlays.items()
        if (label := label_from_instruction(instruction))
    }


def rows_from_overlays(overlays: dict[str, str]) -> list[BinaryWorkbenchRowDTO]:
    return [
        BinaryWorkbenchRowDTO(offsets={"File": offset}, instruction=instruction, bytes_text="")
        for offset, instruction in overlays.items()
    ]


def merged_instruction_labels(
    rows: list[BinaryWorkbenchRowDTO],
    overlays: dict[str, str],
) -> dict[str, str]:
    return {**labels_from_overlays(overlays), **labels_from_rows(rows)}


def file_offset(row: BinaryWorkbenchRowDTO) -> str:
    return row.offsets.get("File", DEFAULT_FILE_OFFSET)


def label_from_instruction(instruction: str) -> str:
    before_comment = instruction.split("#", 1)[0].strip()
    if LABEL_SEPARATOR not in before_comment:
        return ""
    candidate = before_comment.split(LABEL_SEPARATOR, 1)[0].strip()
    return candidate if candidate and " " not in candidate and "\t" not in candidate else ""
