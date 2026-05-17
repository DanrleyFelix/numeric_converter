from __future__ import annotations

from src.core.binary_workbench.mips_r3000a.constants import (
    BRANCH_OPCODES,
    I_OPCODES,
    J_OPCODES,
    R_FUNCTS,
    SPECIAL_BRANCH_RT,
)
from src.core.binary_workbench.mips_r3000a.operands import (
    j_type,
    number,
    offset_operand,
    register,
    r_type,
)


def assemble_fallback(instruction: str, address: int) -> bytes | None:
    parts = instruction.replace(",", " ").split()
    mnemonic = parts[0].lower()
    operands = parts[1:]
    if mnemonic in J_OPCODES and operands:
        return j_type(J_OPCODES[mnemonic], number(operands[0]) >> 2)
    if mnemonic == "jr" and operands:
        return r_type(register(operands[0]), 0, 0, 0, 0x08)
    if mnemonic == "jalr" and operands:
        rs = register(operands[0])
        rd = register(operands[1]) if len(operands) > 1 else 31
        return r_type(rs, 0, rd, 0, 0x09)
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
        return word.to_bytes(4, "little")
    return None


def _assemble_i_type(mnemonic: str, operands: list[str]) -> bytes | None:
    opcode = I_OPCODES[mnemonic]
    if mnemonic == "lui":
        rt, immediate = register(operands[0]), number(operands[1]) & 0xFFFF
        word = (opcode << 26) | (rt << 16) | immediate
        return word.to_bytes(4, "little")
    if mnemonic in {"lw", "sw", "lh", "lhu", "sh", "lb", "lbu", "sb"}:
        rt = register(operands[0])
        immediate, base = offset_operand(operands[1])
        word = (opcode << 26) | (base << 21) | (rt << 16) | (immediate & 0xFFFF)
        return word.to_bytes(4, "little")
    rt, rs, immediate = register(operands[0]), register(operands[1]), number(operands[2])
    word = (opcode << 26) | (rs << 21) | (rt << 16) | (immediate & 0xFFFF)
    return word.to_bytes(4, "little")


def _assemble_branch(mnemonic: str, operands: list[str]) -> bytes:
    opcode = BRANCH_OPCODES[mnemonic]
    if mnemonic in {"blez", "bgtz"}:
        rs = register(operands[0])
        offset = number(operands[1]) & 0xFFFF
        word = (opcode << 26) | (rs << 21) | offset
        return word.to_bytes(4, "little")
    rs, rt = register(operands[0]), register(operands[1])
    offset = number(operands[2]) & 0xFFFF
    word = (opcode << 26) | (rs << 21) | (rt << 16) | offset
    return word.to_bytes(4, "little")
