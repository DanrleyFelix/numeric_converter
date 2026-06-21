from __future__ import annotations

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as _ROW_BYTES
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.binary_workbench.mips_r3000a.preprocessor import editor_mips_instruction
from src.core.binary_workbench.mips_r3000a.source_line_rows import (
    build_source_line_rows,
    empty_source_row,
    labels_from_source_rows,
    offset_values,
)

def build_rows_from_bytes(
    data: bytes,
    offset_names: list[str],
    start_offset: int = 0,
    offset_bases: dict[str, str] | None = None,
) -> list[BinaryWorkbenchRowDTO]:
    codec = PsxMipsR3000ACodec()
    rows: list[BinaryWorkbenchRowDTO] = []
    for relative in range(0, len(data), _ROW_BYTES):
        offset = start_offset + relative
        chunk = data[relative : relative + _ROW_BYTES].ljust(_ROW_BYTES, b"\x00")
        rows.append(
            BinaryWorkbenchRowDTO(
                offsets=offset_values(offset, offset_names, offset_bases or {}),
                instruction=editor_mips_instruction(codec.disassemble(chunk, offset), offset),
                bytes_text=codec.bytes_text(chunk),
            )
        )
    return rows


def build_rows_from_instructions(
    lines: list[str],
    offset_names: list[str],
    offset_bases: dict[str, str] | None = None,
    variables: dict[str, str] | None = None,
    equates: dict[str, str] | None = None,
) -> list[BinaryWorkbenchRowDTO]:
    codec = PsxMipsR3000ACodec()
    rows = build_source_line_rows(
        lines,
        offset_names,
        offset_bases or {},
        codec,
        variables=variables,
        equates=equates,
    )
    return rows or build_scratch_rows(offset_names)


def extract_labels_from_instructions(lines: list[str]) -> dict[str, str]:
    codec = PsxMipsR3000ACodec()
    rows = build_source_line_rows(lines, ["File"], {}, codec)
    return labels_from_source_rows(rows or [], word_size=codec.word_size)


def build_scratch_rows(
    offset_names: list[str],
    offset_bases: dict[str, str] | None = None,
    count: int = 8,
) -> list[BinaryWorkbenchRowDTO]:
    codec = PsxMipsR3000ACodec()
    zero = b"\x00\x00\x00\x00"
    return [
        BinaryWorkbenchRowDTO(
            offsets=offset_values(index * _ROW_BYTES, offset_names, offset_bases or {}),
            instruction=editor_mips_instruction(codec.disassemble(zero, index * _ROW_BYTES), index * _ROW_BYTES),
            bytes_text=codec.bytes_text(zero),
        )
        for index in range(count)
    ]


def rebuild_rows_with_offsets(
    rows: list[BinaryWorkbenchRowDTO],
    offset_names: list[str],
    offset_bases: dict[str, str] | None = None,
) -> list[BinaryWorkbenchRowDTO]:
    rebuilt: list[BinaryWorkbenchRowDTO] = []
    offset = 0
    for row in rows:
        if not row.bytes_text:
            rebuilt.append(empty_source_row(row.instruction, offset_names))
            continue
        rebuilt.append(
            BinaryWorkbenchRowDTO(
                offsets=offset_values(offset, offset_names, offset_bases or {}),
                instruction=row.instruction,
                bytes_text=row.bytes_text,
            )
        )
        offset += _ROW_BYTES
    return rebuilt
