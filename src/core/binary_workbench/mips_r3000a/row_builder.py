from __future__ import annotations

from src.modules.dtos import BinaryWorkbenchRowDTO
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.binary_workbench.mips_r3000a.preprocessor import (
    preprocess_instruction,
    strip_comment,
    strip_label,
)

_RAM_BASE = 0x80010000
_ROW_BYTES = 4
_LABEL_SEPARATOR = ":"


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
                offsets=_offset_values(offset, offset_names, offset_bases),
                instruction=codec.disassemble(chunk, _RAM_BASE + offset),
                bytes_text=codec.bytes_text(chunk),
            )
        )
    return rows


def build_rows_from_instructions(
    lines: list[str],
    offset_names: list[str],
    offset_bases: dict[str, str] | None = None,
) -> list[BinaryWorkbenchRowDTO]:
    codec = PsxMipsR3000ACodec()
    rows: list[BinaryWorkbenchRowDTO] = []
    labels = extract_labels_from_instructions(lines)
    instructions = [_display_instruction(line) for line in lines if _normalized(line)]
    for index, instruction in enumerate(instructions):
        offset = index * _ROW_BYTES
        assembly = preprocess_instruction(instruction, _RAM_BASE + offset, labels, {}, {})
        encoded = codec.assemble(assembly, _RAM_BASE + offset) or b"\x00\x00\x00\x00"
        rows.append(
            BinaryWorkbenchRowDTO(
                offsets=_offset_values(offset, offset_names, offset_bases),
                instruction=instruction.strip(),
                bytes_text=codec.bytes_text(encoded),
            )
        )
    return rows or build_scratch_rows(offset_names)


def extract_labels_from_instructions(lines: list[str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    offset = 0
    for line in lines:
        normalized = _normalized(line)
        if not normalized:
            continue
        label, instruction = _split_label(normalized)
        if label:
            labels[label] = f"0x{offset:08X}"
        if instruction:
            offset += _ROW_BYTES
    return labels


def build_scratch_rows(
    offset_names: list[str],
    offset_bases: dict[str, str] | None = None,
    count: int = 8,
) -> list[BinaryWorkbenchRowDTO]:
    codec = PsxMipsR3000ACodec()
    zero = b"\x00\x00\x00\x00"
    return [
        BinaryWorkbenchRowDTO(
            offsets=_offset_values(index * _ROW_BYTES, offset_names, offset_bases),
            instruction=codec.disassemble(zero, _RAM_BASE + (index * _ROW_BYTES)),
            bytes_text=codec.bytes_text(zero),
        )
        for index in range(count)
    ]


def rebuild_rows_with_offsets(
    rows: list[BinaryWorkbenchRowDTO],
    offset_names: list[str],
    offset_bases: dict[str, str] | None = None,
) -> list[BinaryWorkbenchRowDTO]:
    return [
        BinaryWorkbenchRowDTO(
            offsets=_offset_values(index * _ROW_BYTES, offset_names, offset_bases),
            instruction=row.instruction,
            bytes_text=row.bytes_text,
        )
        for index, row in enumerate(rows)
    ]


def _offset_values(
    offset: int,
    offset_names: list[str],
    offset_bases: dict[str, str] | None = None,
) -> dict[str, str]:
    values: dict[str, str] = {}
    bases = offset_bases or {}
    for name in offset_names:
        base = 0 if name == "File" else int(bases.get(name, "0x0"), 0)
        values[name] = f"0x{base + offset:08X}"
    return values


def _normalized(text: str) -> str:
    return strip_comment(text).strip()


def _display_instruction(text: str) -> str:
    return _normalized(text).strip()


def _strip_label(text: str) -> str:
    return strip_label(text)


def _split_label(text: str) -> tuple[str | None, str]:
    if _LABEL_SEPARATOR not in text:
        return None, text
    left, right = text.split(_LABEL_SEPARATOR, 1)
    candidate = left.strip()
    if not candidate or " " in candidate or "\t" in candidate:
        return None, text
    return candidate, right.strip()

