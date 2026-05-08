from __future__ import annotations

from src.core.binary_workbench.mips_r3000a.constants import (
    BRANCH_OPCODES,
    I_OPCODES,
    REGISTER_NAMES,
    R_FUNCTS,
)
from src.core.binary_workbench.mips_r3000a.operands import hex_or_signed, signed16


def disassemble_fallback(word: int, address: int) -> str:
    if word == 0:
        return "nop"
    opcode = (word >> 26) & 0x3F
    if opcode in {0x02, 0x03}:
        mnemonic = "jal" if opcode == 0x03 else "j"
        return f"{mnemonic} 0x{((word & 0x03FFFFFF) << 2):X}"
    if opcode == 0x00:
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        rd = (word >> 11) & 0x1F
        funct = word & 0x3F
        if funct == 0x08:
            return f"jr ${REGISTER_NAMES.get(rs, 'zero')}"
        if funct == 0x09:
            return f"jalr ${REGISTER_NAMES.get(rs, 'zero')}, ${REGISTER_NAMES.get(rd, 'ra')}"
        mnemonic = _mnemonic_from_funct(funct)
        if mnemonic is not None:
            return (
                f"{mnemonic} ${REGISTER_NAMES.get(rd, 'zero')}, "
                f"${REGISTER_NAMES.get(rs, 'zero')}, ${REGISTER_NAMES.get(rt, 'zero')}"
            )
    if opcode in I_OPCODES.values():
        return _disassemble_i_type(opcode, word)
    if opcode in BRANCH_OPCODES.values() or opcode == 0x01:
        return _disassemble_branch(opcode, word, address)
    return f"word 0x{word:08X}"


def _disassemble_i_type(opcode: int, word: int) -> str:
    rs, rt, imm = (word >> 21) & 0x1F, (word >> 16) & 0x1F, signed16(word & 0xFFFF)
    registers = (REGISTER_NAMES.get(rt, "zero"), REGISTER_NAMES.get(rs, "zero"))
    if opcode == 0x0F:
        return f"lui ${registers[0]}, 0x{word & 0xFFFF:04X}"
    if opcode in {0x23, 0x2B, 0x21, 0x25, 0x29, 0x20, 0x24, 0x28}:
        return f"{_mnemonic_from_opcode(opcode)} ${registers[0]}, {hex_or_signed(imm)}(${registers[1]})"
    return f"{_mnemonic_from_opcode(opcode)} ${registers[0]}, ${registers[1]}, {hex_or_signed(imm)}"


def _disassemble_branch(opcode: int, word: int, address: int) -> str:
    rs, rt, imm = (word >> 21) & 0x1F, (word >> 16) & 0x1F, signed16(word & 0xFFFF)
    target = address + 4 + (imm << 2)
    if opcode == 0x01:
        mnemonic = "bgez" if rt == 0x01 else "bltz"
        return f"{mnemonic} ${REGISTER_NAMES.get(rs, 'zero')}, 0x{target:X}"
    if opcode in {0x06, 0x07}:
        return f"{_mnemonic_from_opcode(opcode)} ${REGISTER_NAMES.get(rs, 'zero')}, 0x{target:X}"
    return (
        f"{_mnemonic_from_opcode(opcode)} ${REGISTER_NAMES.get(rs, 'zero')}, "
        f"${REGISTER_NAMES.get(rt, 'zero')}, 0x{target:X}"
    )


def _mnemonic_from_opcode(opcode: int) -> str:
    mapping = {value: key for key, value in I_OPCODES.items()}
    mapping.update({value: key for key, value in BRANCH_OPCODES.items()})
    return mapping.get(opcode, "word")


def _mnemonic_from_funct(funct: int) -> str | None:
    mapping = {value: key for key, value in R_FUNCTS.items()}
    return mapping.get(funct)
