from __future__ import annotations

import re

from PySide6.QtGui import QColor, QTextCharFormat

from src.modules.dtos import BinaryWorkbenchRowDTO

BYTE_TOKEN = re.compile(r"[0-9A-Fa-f]{2}")
HEX_TOKEN = re.compile(r"0x[0-9A-Fa-f]+")
REGISTER_TOKEN = re.compile(r"\$?[a-zA-Z_][A-Za-z0-9_]*")
COMPLETION_TOKEN = re.compile(r"[@_]?[A-Za-z_][A-Za-z0-9_]*")
VARIABLE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])_[A-Za-z_][A-Za-z0-9_]*")
EQUATE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])@[A-Za-z_][A-Za-z0-9_]*")
BRANCHES = {"beq", "bne", "bgtz", "blez", "bltz", "bgez", "beqz", "bnez"}
JUMPS = {"j", "jal", "jr", "jalr"}
KNOWN_MNEMONICS = {
    *BRANCHES,
    *JUMPS,
    "add",
    "addiu",
    "addu",
    "subu",
    "ori",
    "lui",
    "lw",
    "sw",
    "lh",
    "lhu",
    "sh",
    "lb",
    "lbu",
    "sb",
    "sltiu",
    "nop",
    "word",
    ".word",
    ".byte",
    ".half",
}
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
    code = strip_label(text.split(";", 1)[0]).strip()
    for name, value in variables.items():
        code = code.replace(f"_{name.lstrip('_')}", value)
    for name, value in equates.items():
        code = code.replace(f"@{name.lstrip('@')}", value)
    for name, value in labels.items():
        code = re.sub(
            rf"\b{re.escape(name)}\b",
            f"0x{RAM_BASE + safe_int(value, address):X}",
            code,
        )
    return code


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


def mnemonic_color(token: str) -> str:
    mnemonic = token.strip().lower()
    return "#F08080" if mnemonic in BRANCHES or mnemonic in JUMPS else "#A0DC45"


def register_color(token: str) -> str:
    register = token.lstrip("$").lower()
    if register.startswith(("a", "v")):
        return "#D4AF37"
    if register.startswith(("t", "s")) and register != "sp":
        return "#41C1EC"
    return "#00CFFF"


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
    return mnemonic not in KNOWN_MNEMONICS


def parse_bytes(text: str) -> bytes | None:
    raw = text.replace(" ", "").strip()
    if len(raw) != 8:
        return None
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return None


def group_bytes_text(text: str, group_size: int) -> str:
    raw = text.replace(" ", "")
    width = group_size * 2
    return " ".join(raw[index : index + width] for index in range(0, len(raw), width))
