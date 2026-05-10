from __future__ import annotations

import re

from PySide6.QtGui import QColor, QTextCharFormat

from src.core.binary_workbench.mips_r3000a import preprocess_instruction
from src.modules.dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.editor.constants.highlighter_rules import (
    PSX_MIPS_KNOWN_MNEMONICS,
)

BYTE_TOKEN = re.compile(r"[0-9A-Fa-f]{2}")
HEX_TOKEN = re.compile(r"0x[0-9A-Fa-f]+")
REGISTER_TOKEN = re.compile(r"\$?[a-zA-Z_][A-Za-z0-9_]*")
COMPLETION_TOKEN = re.compile(r"[@_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*")
VARIABLE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])_[A-Za-z_][A-Za-z0-9_]*")
EQUATE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])@[A-Za-z_][A-Za-z0-9_]*")
ROW_BYTES = 4
RAM_BASE = 0x80010000


def address_from_row(row: BinaryWorkbenchRowDTO) -> int:
    return RAM_BASE + int(row.offsets.get("File", "0x0"), 16)


def assembly_for_encoding(
    text: str,
    address: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> str:
    return preprocess_instruction(text, address, labels, variables, equates)


def safe_int(value: str, fallback: int = 0) -> int:
    try:
        return int(value, 0)
    except ValueError:
        return fallback


def tooltip_values(values: dict[str, str]) -> dict[str, str]:
    tooltips: dict[str, str] = {}
    for name, value in values.items():
        number = safe_int(value)
        tooltips[name] = f"{number} | 0x{number:X}"
    return tooltips


def text_format(color: str) -> QTextCharFormat:
    style = QTextCharFormat()
    style.setForeground(QColor(color))
    return style


def strip_label(text: str) -> str:
    _, code = code_without_label(text)
    return code


def code_without_label(text: str) -> tuple[int, str]:
    if ":" not in text:
        return 0, text
    left, right = text.split(":", 1)
    if left.strip() and " " not in left.strip():
        stripped = right.lstrip()
        return len(left) + 1 + (len(right) - len(stripped)), stripped
    return 0, text


def invalid_instruction(text: str) -> bool:
    code = text.strip()
    if not code:
        return False
    mnemonic = code.split()[0].lower()
    return mnemonic not in PSX_MIPS_KNOWN_MNEMONICS


def group_bytes_text(text: str, group_size: int) -> str:
    raw = "".join(text.split()).upper()
    return format_byte_groups(raw, group_size)


def normalize_bytes_text(text: str, group_size: int, uppercase: bool) -> str:
    raw = _normalized_byte_line(text, uppercase)
    return "\n".join(
        format_byte_groups(raw[index : index + (ROW_BYTES * 2)], group_size)
        for index in range(0, len(raw), ROW_BYTES * 2)
    )


def _normalized_byte_line(line: str, uppercase: bool) -> str:
    raw = "".join(line.split())
    return raw.upper() if uppercase else raw


def normalize_instruction_text(text: str, uppercase: bool) -> str:
    normalized = text.upper() if uppercase else text
    return re.sub(r"(?<=0)X", "x", normalized)


def format_byte_groups(raw: str, group_size: int) -> str:
    width = group_size * 2
    return " ".join(raw[index : index + width] for index in range(0, len(raw), width))


def byte_cursor_position(text: str, raw_index: int) -> int:
    if raw_index <= 0:
        return 0
    count = 0
    for position, char in enumerate(text):
        if char.isspace():
            continue
        count += 1
        if count >= raw_index:
            return position + 1
    return len(text)
