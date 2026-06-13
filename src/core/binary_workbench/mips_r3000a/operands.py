from __future__ import annotations

from src.core.binary_workbench.mips_r3000a.constants import REGISTERS


def word_bytes(word: int) -> bytes:
    return (word & 0xFFFFFFFF).to_bytes(4, "little")


def register(token: str) -> int:
    return REGISTERS[token.lstrip("$").lower()]


def number(token: str) -> int:
    return int(token, 16) if token.lower().startswith(("0x", "-0x")) else int(token, 10)


def offset_operand(token: str) -> tuple[int, int]:
    immediate, base = token.split("(", 1)
    return number(immediate), register(base.rstrip(")"))


def r_type(rs: int, rt: int, rd: int, shamt: int, funct: int) -> bytes:
    word = (rs << 21) | (rt << 16) | (rd << 11) | (shamt << 6) | funct
    return word_bytes(word)


def j_type(opcode: int, target: int) -> bytes:
    return word_bytes((opcode << 26) | (target & 0x03FFFFFF))


def signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def hex_or_signed(value: int) -> str:
    return f"-0x{abs(value):X}" if value < 0 else f"0x{value:X}"
