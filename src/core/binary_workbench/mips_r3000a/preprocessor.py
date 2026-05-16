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

WORD_DIRECTIVES = {"word", ".word"}
CORE_NO_OPERAND_MNEMONICS = {"nop"}


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
    return _replace_labels(code, labels, address).strip()


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
    if ":" not in text:
        return text
    left, right = text.split(":", 1)
    candidate = left.strip()
    if candidate and " " not in candidate and "\t" not in candidate:
        return right.lstrip()
    return text


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
