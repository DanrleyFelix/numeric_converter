from __future__ import annotations

from src.modules.binary_workbench_constants import (
    ASSEMBLY_LABEL_SEPARATOR as LABEL_SEPARATOR,
    BINARY_WORKBENCH_DEFAULT_FILE_OFFSET as DEFAULT_FILE_OFFSET,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


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
        if offset == "-":
            continue
        if previous.get(offset) == row.instruction:
            continue
        if row.instruction.strip():
            updated[offset] = row.instruction
        else:
            updated.pop(offset, None)
    return updated


def labels_from_rows(rows: list[BinaryWorkbenchRowDTO]) -> dict[str, str]:
    return labels_from_lines_at_rows([row.instruction for row in rows], rows)


def labels_from_lines_at_rows(
    lines: list[str],
    rows: list[BinaryWorkbenchRowDTO],
) -> dict[str, str]:
    labels: dict[str, str] = {}
    next_offset = "-"
    for line, row in reversed(list(zip(lines, rows))):
        if file_offset(row) != "-":
            next_offset = file_offset(row)
        if (label := label_from_instruction(line)) and next_offset != "-":
            labels[label] = next_offset
    return labels


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
    before_comment = instruction.split(";", 1)[0].split("#", 1)[0].strip()
    if LABEL_SEPARATOR not in before_comment:
        return ""
    definition = before_comment.split(LABEL_SEPARATOR, 1)[0]
    candidate = definition.strip()
    return (
        candidate
        if candidate
        and definition == definition.rstrip()
        and " " not in candidate
        and "\t" not in candidate
        else ""
    )
