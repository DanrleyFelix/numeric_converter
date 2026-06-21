from __future__ import annotations

from src.core.binary_workbench.mips_r3000a import editor_mips_instruction
from src.core.binary_workbench.mips_r3000a.preprocessor import raw_mips_instruction
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_EMPTY_OFFSET as EMPTY_OFFSET,
    BINARY_WORKBENCH_FILE_OFFSET_COLUMN as FILE_OFFSET,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
)
from src.modules.contracts import CPUArchCodec
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO

INVALID_INSTRUCTION_PREFIX = "Invalid instruction:"


def version_instruction_maps(
    rows: list[BinaryWorkbenchRowDTO],
    instruction_overlays: dict[str, str],
    codec: CPUArchCodec,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> tuple[dict[str, str], dict[int, str]]:
    offsets: dict[str, str] = {}
    lines: dict[int, str] = {}
    line_base = _line_base(rows)
    for index, row in enumerate(rows):
        offset_text = row.offsets.get(FILE_OFFSET, EMPTY_OFFSET)
        if offset_text == EMPTY_OFFSET:
            if row.instruction.strip():
                lines[line_base + index] = row.instruction
            continue
        instruction = _version_offset_instruction(
            row,
            instruction_overlays,
            codec,
            labels,
            variables,
            equates,
        )
        if instruction:
            offsets[offset_text] = instruction
    return offsets, lines


def _version_offset_instruction(
    row: BinaryWorkbenchRowDTO,
    instruction_overlays: dict[str, str],
    codec: CPUArchCodec,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> str:
    offset_text = row.offsets.get(FILE_OFFSET, "0x0")
    offset = int(offset_text, 16)
    code, separator, comment = row.instruction.partition(";")
    assembly = raw_mips_instruction(row.instruction, offset, labels, variables, equates)
    data = codec.assemble(assembly, offset) if assembly else None
    if data is None:
        if _comment_only(separator, code):
            return _comment_feedback(row, comment, codec)
        return _invalid_instruction_feedback(row, code, comment, codec)
    if offset_text in instruction_overlays or separator:
        return row.instruction
    expected = row.bytes_text.replace(" ", "").upper()
    return row.instruction if data.hex().upper() != expected else ""


def _invalid_instruction_feedback(
    row: BinaryWorkbenchRowDTO,
    code: str,
    comment: str,
    codec: CPUArchCodec,
) -> str:
    restored = _restored_instruction(row, codec)
    invalid = code.strip()
    if not restored or not invalid:
        return ""
    note = f"{INVALID_INSTRUCTION_PREFIX} {invalid}."
    suffix = f" {comment.lstrip()}" if comment.strip() else ""
    return f"{restored}; {note}{suffix}"


def _comment_feedback(
    row: BinaryWorkbenchRowDTO,
    comment: str,
    codec: CPUArchCodec,
) -> str:
    restored = _restored_instruction(row, codec)
    return f"{restored}; {comment.lstrip()}" if restored and comment.strip() else ""


def _comment_only(separator: str, code: str) -> bool:
    return bool(separator) and not code.strip()


def _restored_instruction(row: BinaryWorkbenchRowDTO, codec: CPUArchCodec) -> str:
    try:
        offset = int(row.offsets.get(FILE_OFFSET, "0x0"), 16)
        data = bytes.fromhex(row.bytes_text.replace(" ", "")).ljust(ROW_BYTES, b"\x00")
    except ValueError:
        return ""
    return editor_mips_instruction(codec.disassemble(data, offset), offset)


def _line_base(rows: list[BinaryWorkbenchRowDTO]) -> int:
    for index, row in enumerate(rows):
        offset = row.offsets.get(FILE_OFFSET, EMPTY_OFFSET)
        if offset != EMPTY_OFFSET:
            return (int(offset, 16) // ROW_BYTES) - index
    return 0
