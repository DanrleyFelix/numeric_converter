from __future__ import annotations

import re

from src.core.binary_workbench.mips_r3000a.constants import (
    BRANCH_OPCODES,
    I_OPCODES,
    J_OPCODES,
    R_FUNCTS,
    R_JUMP_FUNCTS,
    SPECIAL_BRANCH_RT,
)
from src.core.binary_workbench.mips_r3000a.operands import number, signed16

WORD_DIRECTIVES = {"word", ".word"}
CORE_NO_OPERAND_MNEMONICS = {"nop"}
TWO_OPERAND_BRANCHES = {"blez", "bgtz", *SPECIAL_BRANCH_RT}


def preprocess_instruction(
    text: str,
    address: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> str:
    code = strip_label(strip_comment(text)).strip()
    code = _replace_prefixed_symbols(code, "_", variables)
    code = _replace_prefixed_symbols(code, "@", equates)
    code = _replace_labels(code, labels, address)
    return _replace_branch_number(
        code,
        lambda target: _format_branch_immediate((target - (address + 4)) >> 2),
    ).strip()


def editor_mips_instruction(text: str, address: int) -> str:
    label, code = _split_label(strip_comment(text).strip())
    if not _is_branch_code(code):
        return text
    converted = _replace_branch_number(
        code,
        lambda immediate: _format_branch_target(address + 4 + (signed16(immediate & 0xFFFF) << 2)),
    )
    return f"{label}: {converted}" if label else converted


def raw_mips_instruction(
    text: str,
    address: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> str:
    code = preprocess_instruction(text, address, labels, variables, equates)
    return code.lower() if is_core_mips_instruction(code) else ""


def strip_comment(text: str) -> str:
    return text.split(";", 1)[0]


def strip_label(text: str) -> str:
    return _split_label(text)[1]


def is_core_mips_instruction(text: str) -> bool:
    parts = text.strip().split()
    if not parts:
        return False
    return parts[0].lower() in _core_mnemonics()


def _replace_prefixed_symbols(text: str, prefix: str, values: dict[str, str]) -> str:
    result = text
    for name, value in values.items():
        symbol = f"{prefix}{name.lstrip(prefix)}"
        result = re.sub(re.escape(symbol), value, result, flags=re.IGNORECASE)
    return result


def _replace_labels(text: str, labels: dict[str, str], fallback: int) -> str:
    result = text
    for name, value in labels.items():
        target = _safe_int(value, fallback)
        result = re.sub(rf"\b{re.escape(name)}\b", f"0x{target:x}", result, flags=re.IGNORECASE)
    return result


def _safe_int(value: str, fallback: int) -> int:
    try:
        return int(value, 0)
    except ValueError:
        return fallback


def _replace_branch_number(text: str, formatter) -> str:
    tokens = text.replace(",", " ").split()
    if not tokens:
        return text
    operand_index = _branch_operand_index(tokens[0].lower())
    if operand_index is None or len(tokens) <= operand_index + 1:
        return text
    try:
        value = number(tokens[operand_index + 1])
    except ValueError:
        return text
    operands = tokens[1:]
    operands[operand_index] = formatter(value)
    return f"{tokens[0]} {', '.join(operands)}"


def _branch_operand_index(mnemonic: str) -> int | None:
    if mnemonic in TWO_OPERAND_BRANCHES:
        return 1
    if mnemonic in BRANCH_OPCODES:
        return 2
    return None


def _is_branch_code(text: str) -> bool:
    parts = text.replace(",", " ").split()
    return bool(parts) and _branch_operand_index(parts[0].lower()) is not None


def _format_branch_immediate(value: int) -> str:
    signed = signed16(value & 0xFFFF)
    return f"-0x{abs(signed):X}" if signed < 0 else f"0x{signed:04X}"


def _format_branch_target(value: int) -> str:
    return f"-0x{abs(value):08X}" if value < 0 else f"0x{value:08X}"


def _split_label(text: str) -> tuple[str, str]:
    if ":" not in text:
        return "", text
    left, right = text.split(":", 1)
    candidate = left.strip()
    if candidate and " " not in candidate and "\t" not in candidate:
        return candidate, right.lstrip()
    return "", text


def _core_mnemonics() -> set[str]:
    return {
        *BRANCH_OPCODES,
        *I_OPCODES,
        *J_OPCODES,
        *R_FUNCTS,
        *R_JUMP_FUNCTS,
        *SPECIAL_BRANCH_RT,
        *CORE_NO_OPERAND_MNEMONICS,
        *WORD_DIRECTIVES,
    }
