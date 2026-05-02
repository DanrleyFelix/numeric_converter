from __future__ import annotations

from src.modules.dtos import BinaryWorkbenchRowDTO
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec

_RAM_BASE = 0x80010000
_ROW_BYTES = 4


def build_rows_from_bytes(data: bytes, offset_names: list[str]) -> list[BinaryWorkbenchRowDTO]:
    codec = PsxMipsR3000ACodec()
    rows: list[BinaryWorkbenchRowDTO] = []
    for index in range(0, max(len(data), _ROW_BYTES * 8), _ROW_BYTES):
        chunk = data[index : index + _ROW_BYTES].ljust(_ROW_BYTES, b"\x00")
        rows.append(
            BinaryWorkbenchRowDTO(
                offsets=_offset_values(index, offset_names),
                instruction=codec.disassemble(chunk, _RAM_BASE + index),
                bytes_text=codec.bytes_text(chunk),
            )
        )
    return rows


def build_rows_from_instructions(lines: list[str], offset_names: list[str]) -> list[BinaryWorkbenchRowDTO]:
    codec = PsxMipsR3000ACodec()
    rows: list[BinaryWorkbenchRowDTO] = []
    for index, instruction in enumerate(line for line in lines if line.strip()):
        offset = index * _ROW_BYTES
        encoded = codec.assemble(instruction, _RAM_BASE + offset) or b"\x00\x00\x00\x00"
        rows.append(
            BinaryWorkbenchRowDTO(
                offsets=_offset_values(offset, offset_names),
                instruction=codec.disassemble(encoded, _RAM_BASE + offset),
                bytes_text=codec.bytes_text(encoded),
            )
        )
    return rows or build_scratch_rows(offset_names)


def build_scratch_rows(offset_names: list[str], count: int = 8) -> list[BinaryWorkbenchRowDTO]:
    codec = PsxMipsR3000ACodec()
    zero = b"\x00\x00\x00\x00"
    return [
        BinaryWorkbenchRowDTO(
            offsets=_offset_values(index * _ROW_BYTES, offset_names),
            instruction=codec.disassemble(zero, _RAM_BASE + (index * _ROW_BYTES)),
            bytes_text=codec.bytes_text(zero),
        )
        for index in range(count)
    ]


def _offset_values(offset: int, offset_names: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in offset_names:
        values[name] = f"0x{(0 if name == 'File' else _RAM_BASE) + offset:08X}"
    return values
