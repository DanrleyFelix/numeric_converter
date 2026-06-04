from __future__ import annotations

import re

from src.core.binary_workbench.mips_r3000a import raw_mips_instruction
from src.modules.contracts import CPUArchCodec
from src.modules.dtos import BinaryWorkbenchRowDTO

FILE_OFFSET_COLUMN = "File"
DEFAULT_FILE_OFFSET = "0x00000000"
NUMBER_TOKEN = re.compile(r"(?<![\w$])-?(?:0x[0-9A-Fa-f]+|\d+)(?!\w)")
MEMORY_OPERAND_TOKEN = re.compile(r"(?<![\w$])-?(?:0x[0-9A-Fa-f]+|\d+)\(\$?[A-Za-z][A-Za-z0-9_]*\)")


def apply_symbol_offsets(
    rows: list[BinaryWorkbenchRowDTO],
    variables: dict[str, str],
    equates: dict[str, str],
    symbol_offsets: dict[str, list[str]],
    codec: CPUArchCodec,
) -> list[BinaryWorkbenchRowDTO]:
    return [
        BinaryWorkbenchRowDTO(
            offsets=row.offsets,
            instruction=with_offset_symbols(row, variables, equates, symbol_offsets, codec),
            bytes_text=row.bytes_text,
        )
        for row in rows
    ]


def with_offset_symbols(
    row: BinaryWorkbenchRowDTO,
    variables: dict[str, str],
    equates: dict[str, str],
    symbol_offsets: dict[str, list[str]],
    codec: CPUArchCodec,
) -> str:
    offset = file_offset(row)
    if not row.bytes_text or offset == "-":
        return row.instruction
    code = row.instruction
    for symbol in _symbols_for_offset(offset, variables, equates, symbol_offsets):
        code = replace_matching_symbol(code, symbol, row.bytes_text, int(offset, 16), {}, variables, equates, codec)
    return code


def replace_matching_symbol(
    instruction: str,
    symbol: str,
    bytes_text: str,
    address: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    codec: CPUArchCodec,
) -> str:
    matches = list(MEMORY_OPERAND_TOKEN.finditer(instruction)) if symbol.startswith("_") else []
    matches.extend(NUMBER_TOKEN.finditer(instruction))
    for match in matches:
        candidate = f"{instruction[: match.start()]}{symbol}{instruction[match.end() :]}"
        if _assembles_to_bytes(candidate, bytes_text, address, labels, variables, equates, codec):
            return candidate
    return instruction


def file_offset(row: BinaryWorkbenchRowDTO) -> str:
    return row.offsets.get(FILE_OFFSET_COLUMN, DEFAULT_FILE_OFFSET)


def _assembles_to_bytes(
    instruction: str,
    bytes_text: str,
    address: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    codec: CPUArchCodec,
) -> bool:
    assembly = raw_mips_instruction(instruction, address, labels, variables, equates)
    data = codec.assemble(assembly, address) if assembly else None
    return data == bytes.fromhex(bytes_text.replace(" ", ""))


def _symbols_for_offset(
    offset: str,
    variables: dict[str, str],
    equates: dict[str, str],
    symbol_offsets: dict[str, list[str]],
) -> list[str]:
    symbols: list[str] = []
    for name in variables:
        if offset in symbol_offsets.get(name, []):
            symbols.append(f"_{name.lstrip('_')}")
    for name in equates:
        if offset in symbol_offsets.get(name, []):
            symbols.append(f"@{name.lstrip('@')}")
    return symbols
