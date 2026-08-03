from __future__ import annotations

from src.core.binary_workbench.mips_r3000a.constants import (
    BRANCH_OPCODES,
    I_OPCODES,
    J_OPCODES,
    R_CODE_FUNCTS,
    R_FUNCTS,
    R_JUMP_FUNCTS,
    SPECIAL_BRANCH_RT,
)
from src.core.binary_workbench.mips_r3000a.comments import strip_comment
from src.core.binary_workbench.mips_r3000a.operands import number, signed16
from src.core.binary_workbench.mips_r3000a.symbol_resolver import MipsSymbolResolver

WORD_DIRECTIVES = {"word", ".word"}
CORE_NO_OPERAND_MNEMONICS = {"nop"}
TWO_OPERAND_BRANCHES = {"blez", "bgtz", *SPECIAL_BRANCH_RT}
LOAD_IMMEDIATE_PSEUDO = "li"
ZERO_BRANCH_PSEUDOS = {
    "beqz": "beq",
    "bnez": "bne",
}
SHORT_IMMEDIATE_MIN = -0x8000
SHORT_IMMEDIATE_MAX = 0x7FFF
MIPS_HALF_MASK = 0xFFFF
MIPS_HALF_SHIFT = 16
SHORT_DESTINATION_IMMEDIATE = {"addi", "addiu", "andi", "ori", "slti", "sltiu", "xori"}
SHORT_DESTINATION_REGISTER = {
    "add", "addu", "and", "nor", "or", "sll", "sllv", "slt", "sltu",
    "sra", "srav", "srl", "srlv", "sub", "subu", "xor",
}


def preprocess_instruction(
    text: str,
    address: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    resolver: MipsSymbolResolver | None = None,
) -> str:
    code = strip_label(strip_comment(text)).strip()
    code = expand_short_instruction(code)
    mnemonic = _instruction_mnemonic(code)
    code = (resolver or MipsSymbolResolver(labels, variables, equates)).replace(
        code,
        address,
        mnemonic,
    )
    code = _replace_load_immediate_pseudo(code)
    code = _replace_zero_branch_pseudo(code)
    return _replace_branch_number(
        code,
        lambda target: _format_branch_immediate((target - (address + 4)) >> 2),
    ).strip()


def expand_short_instruction(text: str) -> str:
    """Expand a two-operand destination form by repeating its destination."""

    tokens = text.replace(",", " ").split()
    if len(tokens) != 3:
        return text
    mnemonic = tokens[0].lower()
    if mnemonic not in SHORT_DESTINATION_IMMEDIATE | SHORT_DESTINATION_REGISTER:
        return text
    return f"{tokens[0]} {tokens[1]}, {tokens[1]}, {tokens[2]}"


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
    resolver: MipsSymbolResolver | None = None,
) -> str:
    code = preprocess_instruction(
        text,
        address,
        labels,
        variables,
        equates,
        resolver,
    )
    return code.lower() if is_core_mips_instruction(code) else ""




def strip_label(text: str) -> str:
    return _split_label(text)[1]


def is_core_mips_instruction(text: str) -> bool:
    parts = text.strip().split()
    if not parts:
        return False
    return parts[0].lower() in _core_mnemonics()


def _instruction_mnemonic(text: str) -> str:
    parts = text.replace(",", " ").split()
    return parts[0].lower() if parts else ""


def _replace_load_immediate_pseudo(text: str) -> str:
    tokens = text.replace(",", " ").split()
    if len(tokens) != 3 or tokens[0].lower() != LOAD_IMMEDIATE_PSEUDO:
        return text
    try:
        value = int(tokens[2], 0)
    except ValueError:
        return text
    if SHORT_IMMEDIATE_MIN <= value <= MIPS_HALF_MASK:
        return f"addiu {tokens[1]}, $zero, {tokens[2]}"
    if value & MIPS_HALF_MASK == 0:
        return f"lui {tokens[1]}, 0x{(value >> MIPS_HALF_SHIFT) & MIPS_HALF_MASK:x}"
    return text


def _replace_zero_branch_pseudo(text: str) -> str:
    tokens = text.replace(",", " ").split()
    if len(tokens) != 3:
        return text
    mnemonic = tokens[0].lower()
    if mnemonic not in ZERO_BRANCH_PSEUDOS:
        return text
    return f"{ZERO_BRANCH_PSEUDOS[mnemonic]} {tokens[1]}, $zero, {tokens[2]}"


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
    if candidate and left == left.rstrip() and " " not in candidate and "\t" not in candidate:
        return candidate, right.lstrip()
    return "", text


def _core_mnemonics() -> set[str]:
    return {
        *BRANCH_OPCODES,
        *I_OPCODES,
        *J_OPCODES,
        *R_CODE_FUNCTS,
        *R_FUNCTS,
        *R_JUMP_FUNCTS,
        *SPECIAL_BRANCH_RT,
        *CORE_NO_OPERAND_MNEMONICS,
        *WORD_DIRECTIVES,
    }
