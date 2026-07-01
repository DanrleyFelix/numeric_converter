from __future__ import annotations

from src.core.binary_workbench.mips_r3000a.constants import (
    BRANCH_OPCODES,
    I_OPCODES,
    J_OPCODES,
    R_CODE_FUNCTS,
    R_FUNCTS,
    R_MOVE_FROM_HILO,
    R_MOVE_TO_HILO,
    R_MULT_DIV,
    R_SHIFT_IMMEDIATE,
    R_SHIFT_VARIABLE,
    SPECIAL_BRANCH_RT,
)
from src.core.binary_workbench.mips_r3000a.operands import (
    j_type,
    number,
    offset_operand,
    register,
    r_type,
    word_bytes,
)

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


def assemble_fallback(instruction: str, address: int) -> bytes | None:
    parts = instruction.replace(",", " ").split()
    mnemonic = parts[0].lower()
    operands = parts[1:]
    if mnemonic == "nop":
        return word_bytes(0)
    if mnemonic in J_OPCODES and operands:
        return j_type(J_OPCODES[mnemonic], number(operands[0]) >> 2)
    if mnemonic == "jr" and operands:
        return r_type(register(operands[0]), 0, 0, 0, 0x08)
    if mnemonic == "jalr" and operands:
        rd = register(operands[0]) if len(operands) > 1 else 31
        rs = register(operands[1]) if len(operands) > 1 else register(operands[0])
        return r_type(rs, 0, rd, 0, 0x09)
    if mnemonic in R_SHIFT_IMMEDIATE:
        rd, rt = register(operands[0]), register(operands[1])
        return r_type(0, rt, rd, number(operands[2]) & 0x1F, R_FUNCTS[mnemonic])
    if mnemonic in R_SHIFT_VARIABLE:
        rd, rt, rs = register(operands[0]), register(operands[1]), register(operands[2])
        return r_type(rs, rt, rd, 0, R_FUNCTS[mnemonic])
    if mnemonic in R_MOVE_FROM_HILO:
        return r_type(0, 0, register(operands[0]), 0, R_FUNCTS[mnemonic])
    if mnemonic in R_MOVE_TO_HILO:
        return r_type(register(operands[0]), 0, 0, 0, R_FUNCTS[mnemonic])
    if mnemonic in R_MULT_DIV:
        return r_type(register(operands[0]), register(operands[1]), 0, 0, R_FUNCTS[mnemonic])
    if mnemonic in R_CODE_FUNCTS:
        code = number(operands[0]) if operands else 0
        return word_bytes(((code & 0xFFFFF) << 6) | R_CODE_FUNCTS[mnemonic])
    if mnemonic in R_FUNCTS:
        rd, rs, rt = register(operands[0]), register(operands[1]), register(operands[2])
        return r_type(rs, rt, rd, 0, R_FUNCTS[mnemonic])
    if mnemonic in I_OPCODES:
        return _assemble_i_type(mnemonic, operands)
    if mnemonic in BRANCH_OPCODES:
        return _assemble_branch(mnemonic, operands)
    if mnemonic in SPECIAL_BRANCH_RT:
        offset = number(operands[1]) & 0xFFFF
        word = (
            (0x01 << 26)
            | (register(operands[0]) << 21)
            | (SPECIAL_BRANCH_RT[mnemonic] << 16)
            | offset
        )
        return word_bytes(word)
    return None


def _assemble_i_type(mnemonic: str, operands: list[str]) -> bytes:
    opcode = I_OPCODES[mnemonic]
    if mnemonic == "lui":
        rt, immediate = register(operands[0]), number(operands[1]) & 0xFFFF
        word = (opcode << 26) | (rt << 16) | immediate
        return word_bytes(word)
    if mnemonic in MEMORY_MNEMONICS:
        rt = register(operands[0])
        immediate, base = offset_operand(operands[1])
        word = (opcode << 26) | (base << 21) | (rt << 16) | (immediate & 0xFFFF)
        return word_bytes(word)
    rt, rs, immediate = register(operands[0]), register(operands[1]), number(operands[2])
    word = (opcode << 26) | (rs << 21) | (rt << 16) | (immediate & 0xFFFF)
    return word_bytes(word)


def _assemble_branch(mnemonic: str, operands: list[str]) -> bytes:
    opcode = BRANCH_OPCODES[mnemonic]
    if mnemonic in {"blez", "bgtz"}:
        rs = register(operands[0])
        offset = number(operands[1]) & 0xFFFF
        word = (opcode << 26) | (rs << 21) | offset
        return word_bytes(word)
    rs, rt = register(operands[0]), register(operands[1])
    offset = number(operands[2]) & 0xFFFF
    word = (opcode << 26) | (rs << 21) | (rt << 16) | offset
    return word_bytes(word)
