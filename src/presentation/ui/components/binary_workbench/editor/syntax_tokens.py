from __future__ import annotations

import re

from PySide6.QtGui import QColor, QTextCharFormat

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.constants import HEX_DIGIT_PATTERN
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.editor.constants.highlighter_rules import (
    PSX_MIPS_KNOWN_MNEMONICS,
)

BYTE_TOKEN = re.compile(rf"{HEX_DIGIT_PATTERN}{{2}}")
HEX_TOKEN = re.compile(rf"0x{HEX_DIGIT_PATTERN}+", re.IGNORECASE)
DECIMAL_TOKEN = re.compile(r"(?<![\w$])\d+(?![\w])")
REGISTER_TOKEN = re.compile(r"\$?[a-zA-Z_][A-Za-z0-9_]*")
COMPLETION_TOKEN = re.compile(r"/[A-Za-z0-9_]*|[@_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*")
VARIABLE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])_[A-Za-z_][A-Za-z0-9_]*")
EQUATE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])@[A-Za-z_][A-Za-z0-9_]*")
def address_from_row(row: BinaryWorkbenchRowDTO) -> int:
    return safe_int(row.offsets.get("File", "0x0"))


def safe_int(value: str, fallback: int = 0) -> int:
    try:
        return int(value, 0)
    except ValueError:
        return fallback


def tooltip_values(values: dict[str, str]) -> dict[str, str]:
    tooltips: dict[str, str] = {}
    for name, value in values.items():
        try:
            number = int(value, 0)
        except ValueError:
            tooltips[name] = value
            continue
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
    candidate = left.strip()
    if candidate and left == left.rstrip() and " " not in candidate and "\t" not in candidate:
        stripped = right.lstrip()
        return len(left) + 1 + (len(right) - len(stripped)), stripped
    return 0, text


def invalid_instruction(text: str) -> bool:
    code = text.strip()
    if not code:
        return False
    mnemonic = code.split()[0].lower()
    return mnemonic not in PSX_MIPS_KNOWN_MNEMONICS


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
    return "\n".join(
        _normalize_instruction_line(line, uppercase)
        for line in text.split("\n")
    )


def _normalize_instruction_line(line: str, uppercase: bool) -> str:
    code, separator, comment = line.partition(";")
    label, label_separator, body = _partition_label(code)
    if uppercase:
        body = _uppercase_hex_values(body)
        if label_separator or ":" not in code:
            body = _uppercase_mnemonic(body)
    return f"{label}{label_separator}{body}{separator}{comment}"

def _partition_label(text: str) -> tuple[str, str, str]:
    left, separator, right = text.partition(":")
    if not separator:
        return "", "", text
    candidate = left.strip()
    if candidate and left == left.rstrip() and " " not in candidate and "\t" not in candidate:
        return left, separator, right
    return "", "", text


def _uppercase_mnemonic(text: str) -> str:
    match = re.search(r"[A-Za-z.][A-Za-z0-9_.]*(?=\s)", text)
    if match is None or match.group(0).lower() not in PSX_MIPS_KNOWN_MNEMONICS:
        return text
    return f"{text[: match.start()]}{match.group(0).upper()}{text[match.end() :]}"


def _uppercase_hex_values(text: str) -> str:
    return HEX_TOKEN.sub(lambda match: f"0x{match.group(0)[2:].upper()}", text)


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
