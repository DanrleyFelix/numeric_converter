from __future__ import annotations

from src.core.binary_workbench.masked_search import MaskedBytePattern
from src.core.binary_workbench.mips_r3000a.constants import (
    BRANCH_OPCODES,
    I_OPCODES,
    J_OPCODES,
    R_FUNCTS,
    R_JUMP_FUNCTS,
    SPECIAL_BRANCH_RT,
)

WORD_BYTES = 4
OPCODE_MASK = 0xFC000000
R_TYPE_MASK = 0xFC00003F
SPECIAL_BRANCH_MASK = 0xFC1F0000


def mips_instruction_byte_pattern(query: str) -> MaskedBytePattern | None:
    parts = query.replace(",", " ").split()
    if len(parts) != 1:
        return None
    mnemonic = parts[0].lower()
    if mnemonic in I_OPCODES:
        return _word_pattern(I_OPCODES[mnemonic] << 26, OPCODE_MASK)
    if mnemonic in BRANCH_OPCODES:
        return _word_pattern(BRANCH_OPCODES[mnemonic] << 26, OPCODE_MASK)
    if mnemonic in J_OPCODES:
        return _word_pattern(J_OPCODES[mnemonic] << 26, OPCODE_MASK)
    if mnemonic in SPECIAL_BRANCH_RT:
        value = (0x01 << 26) | (SPECIAL_BRANCH_RT[mnemonic] << 16)
        return _word_pattern(value, SPECIAL_BRANCH_MASK)
    if mnemonic in R_JUMP_FUNCTS:
        return _word_pattern(R_JUMP_FUNCTS[mnemonic], R_TYPE_MASK)
    if mnemonic in R_FUNCTS:
        return _word_pattern(R_FUNCTS[mnemonic], R_TYPE_MASK)
    return None


def _word_pattern(value: int, mask: int) -> MaskedBytePattern:
    return MaskedBytePattern(
        needle=value.to_bytes(WORD_BYTES, "little"),
        mask=mask.to_bytes(WORD_BYTES, "little"),
        alignment=WORD_BYTES,
    )
