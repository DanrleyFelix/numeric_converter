from __future__ import annotations

import re

from src.modules.contracts import CPUArchCodec
from src.modules.dtos import BinaryWorkbenchRowDTO
from src.core.binary_workbench.symbolic_replacements import (
    apply_symbol_offsets,
    replace_matching_symbol,
    with_offset_symbols,
)

FILE_OFFSET_COLUMN = "File"
DEFAULT_FILE_OFFSET = "0x00000000"
LABEL_SEPARATOR = ":"


def preserve_symbolic_rows(
    rows: list[BinaryWorkbenchRowDTO],
    previous_rows: list[BinaryWorkbenchRowDTO],
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    codec: CPUArchCodec,
    symbol_offsets: dict[str, list[str]] | None = None,
) -> list[BinaryWorkbenchRowDTO]:
    previous_by_offset = {file_offset(row): row for row in previous_rows}
    return [
        _preserve_symbolic_row(
            row,
            previous_by_offset.get(file_offset(row)),
            labels,
            variables,
            equates,
            codec,
            symbol_offsets or {},
        )
        for row in rows
    ]


def file_offset(row: BinaryWorkbenchRowDTO) -> str:
    return row.offsets.get(FILE_OFFSET_COLUMN, DEFAULT_FILE_OFFSET)


def _preserve_symbolic_row(
    row: BinaryWorkbenchRowDTO,
    previous: BinaryWorkbenchRowDTO | None,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    codec: CPUArchCodec,
    symbol_offsets: dict[str, list[str]],
) -> BinaryWorkbenchRowDTO:
    if previous is None:
        instruction = with_offset_symbols(row, variables, equates, symbol_offsets, codec)
        return BinaryWorkbenchRowDTO(row.offsets, instruction, row.bytes_text)
    if not row.bytes_text or file_offset(row) == "-":
        return row
    if previous.bytes_text == row.bytes_text:
        return previous
    instruction = symbolic_instruction(
        row.instruction,
        previous.instruction,
        row.bytes_text, int(file_offset(row), 16),
        labels,
        variables,
        equates,
        codec,
    )
    return BinaryWorkbenchRowDTO(offsets=row.offsets, instruction=instruction, bytes_text=row.bytes_text)


def symbolic_instruction(
    instruction: str,
    previous_instruction: str,
    bytes_text: str,
    address: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    codec: CPUArchCodec,
) -> str:
    previous_body, comment = _split_comment(previous_instruction)
    label, previous_code = _split_label(previous_body)
    code = _with_matching_symbols(instruction, previous_code, bytes_text, address, labels, variables, equates, codec)
    updated = f"{label}: {code}" if label else code
    return f"{updated}{comment}"


def _with_matching_symbols(
    instruction: str,
    previous_code: str,
    bytes_text: str,
    address: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    codec: CPUArchCodec,
) -> str:
    code = instruction
    for symbol in _symbols_in_previous_code(previous_code, labels, variables, equates):
        code = replace_matching_symbol(code, symbol, bytes_text, address, labels, variables, equates, codec)
    return code


def _symbols_in_previous_code(
    previous_code: str,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> list[str]:
    return [
        *_matching_labels(previous_code, labels),
        *_matching_prefixed_symbols(previous_code, "_", variables),
        *_matching_prefixed_symbols(previous_code, "@", equates),
    ]


def _matching_labels(text: str, labels: dict[str, str]) -> list[str]:
    matches: list[str] = []
    for label in labels:
        if found := re.search(rf"\b{re.escape(label)}\b", text, flags=re.IGNORECASE):
            matches.append(found.group(0))
    return matches


def _matching_prefixed_symbols(text: str, prefix: str, values: dict[str, str]) -> list[str]:
    known = {name.lstrip(prefix).lower() for name in values}
    return [
        match.group(0)
        for match in re.finditer(rf"{re.escape(prefix)}[A-Za-z_][A-Za-z0-9_]*", text)
        if match.group(0).lstrip(prefix).lower() in known
    ]


def _split_label(instruction: str) -> tuple[str, str]:
    if LABEL_SEPARATOR not in instruction:
        return "", instruction
    left, right = instruction.split(LABEL_SEPARATOR, 1)
    label = left.strip()
    if not label or " " in label or "\t" in label:
        return "", instruction
    return label, right.lstrip()


def _split_comment(instruction: str) -> tuple[str, str]:
    index = instruction.find(";")
    if index < 0:
        return instruction, ""
    code = instruction[:index].rstrip()
    return code, instruction[len(code) :]
