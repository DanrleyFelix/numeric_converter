from __future__ import annotations

from src.core.binary_workbench.mips_r3000a.constants import (
    BRANCH_OPCODES,
    I_OPCODES,
    REGISTER_NAMES,
    R_CODE_FUNCTS,
    R_FUNCTS,
    R_MOVE_FROM_HILO,
    R_MOVE_TO_HILO,
    R_MULT_DIV,
    R_SHIFT_IMMEDIATE,
    R_SHIFT_VARIABLE,
)
from src.core.binary_workbench.mips_r3000a.operands import hex_or_signed, signed16

MEMORY_MNEMONICS = {
    "lb",
    "lbu",
    "lh",
    "lhu",
    "lwl",
    "lw",
    "lwr",
    "sb",
    "sh",
    "swl",
    "sw",
    "swr",
}
MEMORY_OPCODES = {I_OPCODES[name] for name in MEMORY_MNEMONICS}
UNSIGNED_IMMEDIATE_OPCODES = {I_OPCODES[name] for name in {"andi", "ori", "xori"}}


def disassemble_fallback(word: int, address: int) -> str:
    if word == 0:
        return "nop"
    opcode = (word >> 26) & 0x3F
    if opcode in {0x02, 0x03}:
        mnemonic = "jal" if opcode == 0x03 else "j"
        target = ((address + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        return f"{mnemonic} 0x{target:X}"
    if opcode == 0x00:
        return _disassemble_r_type(word)
    if opcode in I_OPCODES.values():
        return _disassemble_i_type(opcode, word)
    if opcode in BRANCH_OPCODES.values() or opcode == 0x01:
        return _disassemble_branch(opcode, word)
    return f"word 0x{word:08X}"


def _disassemble_r_type(word: int) -> str:
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    if funct == 0x08:
        return f"jr ${_register_name(rs)}"
    if funct == 0x09:
        if rd == 0x1F:
            return f"jalr ${_register_name(rs)}"
        return f"jalr ${_register_name(rd)}, ${_register_name(rs)}"
    mnemonic = _mnemonic_from_funct(funct)
    if mnemonic in R_SHIFT_IMMEDIATE:
        return f"{mnemonic} ${_register_name(rd)}, ${_register_name(rt)}, 0x{shamt:X}"
    if mnemonic in R_SHIFT_VARIABLE:
        return f"{mnemonic} ${_register_name(rd)}, ${_register_name(rt)}, ${_register_name(rs)}"
    if mnemonic in R_MOVE_FROM_HILO:
        return f"{mnemonic} ${_register_name(rd)}"
    if mnemonic in R_MOVE_TO_HILO:
        return f"{mnemonic} ${_register_name(rs)}"
    if mnemonic in R_MULT_DIV:
        return f"{mnemonic} ${_register_name(rs)}, ${_register_name(rt)}"
    code_mnemonic = _code_mnemonic_from_funct(funct)
    if code_mnemonic is not None:
        code = (word >> 6) & 0xFFFFF
        suffix = f" 0x{code:X}" if code else ""
        return f"{code_mnemonic}{suffix}"
    if mnemonic is not None:
        return (
            f"{mnemonic} ${_register_name(rd)}, "
            f"${_register_name(rs)}, ${_register_name(rt)}"
        )
    return f"word 0x{word:08X}"


def _disassemble_i_type(opcode: int, word: int) -> str:
    rs, rt = (word >> 21) & 0x1F, (word >> 16) & 0x1F
    raw_immediate = word & 0xFFFF
    immediate = signed16(raw_immediate)
    if opcode == I_OPCODES["lui"]:
        return f"lui ${_register_name(rt)}, 0x{raw_immediate:04X}"
    if opcode in MEMORY_OPCODES:
        return (
            f"{_mnemonic_from_opcode(opcode)} ${_register_name(rt)}, "
            f"{hex_or_signed(immediate)}(${_register_name(rs)})"
        )
    immediate_text = (
        f"0x{raw_immediate:04X}"
        if opcode in UNSIGNED_IMMEDIATE_OPCODES
        else hex_or_signed(immediate)
    )
    return (
        f"{_mnemonic_from_opcode(opcode)} ${_register_name(rt)}, "
        f"${_register_name(rs)}, {immediate_text}"
    )


def _disassemble_branch(opcode: int, word: int) -> str:
    rs, rt, imm = (word >> 21) & 0x1F, (word >> 16) & 0x1F, signed16(word & 0xFFFF)
    immediate = _branch_immediate(imm)
    if opcode == 0x01:
        if rt not in {0x00, 0x01}:
            return f"word 0x{word:08X}"
        mnemonic = "bgez" if rt == 0x01 else "bltz"
        return f"{mnemonic} ${_register_name(rs)}, {immediate}"
    if opcode in {0x06, 0x07}:
        return f"{_mnemonic_from_opcode(opcode)} ${_register_name(rs)}, {immediate}"
    return (
        f"{_mnemonic_from_opcode(opcode)} ${_register_name(rs)}, "
        f"${_register_name(rt)}, {immediate}"
    )


def _branch_immediate(value: int) -> str:
    return f"-0x{abs(value):X}" if value < 0 else f"0x{value:04X}"


def _register_name(index: int) -> str:
    return REGISTER_NAMES.get(index, "zero")


def _mnemonic_from_opcode(opcode: int) -> str:
    mapping = {value: key for key, value in I_OPCODES.items()}
    mapping.update({value: key for key, value in BRANCH_OPCODES.items()})
    return mapping.get(opcode, "word")


def _mnemonic_from_funct(funct: int) -> str | None:
    mapping = {value: key for key, value in R_FUNCTS.items()}
    return mapping.get(funct)


def _code_mnemonic_from_funct(funct: int) -> str | None:
    mapping = {value: key for key, value in R_CODE_FUNCTS.items()}
    return mapping.get(funct)
