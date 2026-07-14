from __future__ import annotations

import re
from collections.abc import Mapping

from src.core.binary_workbench.mips_r3000a.constants import REGISTERS
from src.core.binary_workbench.mips_r3000a.operands import signed16

_MEMORY_OPERAND = re.compile(r"(?P<offset>[^()]*)\((?P<base>[^()]+)\)")
_IMMEDIATE_WRITERS = {"addi", "addiu", "andi", "ori", "slti", "sltiu", "xori"}
_REGISTER_WRITERS = {"add", "addu", "and", "nor", "or", "slt", "sltu", "sub", "subu", "xor"}
_SHIFT_IMMEDIATE_WRITERS = {"sll", "sra", "srl"}
_SHIFT_VARIABLE_WRITERS = {"sllv", "srav", "srlv"}
_UNKNOWN_DESTINATION_WRITERS = {
    "lb", "lbu", "lh", "lhu", "lwl", "lw", "lwr", "mfhi", "mflo"
}


def known_register_values_after(
    instruction: str,
    previous: Mapping[int, int] | None = None,
) -> dict[int, int]:
    """Return statically known register values after one MIPS instruction."""

    values = dict(previous or {})
    values[0] = 0
    parts = instruction.replace(",", " ").split()
    if not parts:
        return values
    mnemonic, operands = parts[0].lower(), parts[1:]
    destination = _register_index(operands[0]) if operands else None
    result = _computed_destination(mnemonic, operands, values)
    if destination is not None and destination != 0:
        if result is not None:
            values[destination] = result & 0xFFFFFFFF
        elif _writes_destination(mnemonic):
            values.pop(destination, None)
    return values


def effective_memory_address(
    operand: str,
    known_registers: Mapping[int, int],
) -> int | None:
    """Resolve a memory operand when its base register value is known."""

    match = _MEMORY_OPERAND.fullmatch(operand.strip())
    if match is None:
        return None
    register = _register_index(match.group("base"))
    if register is None or register not in known_registers:
        return None
    try:
        immediate = int(match.group("offset").strip() or "0", 0)
    except ValueError:
        return None
    return (known_registers[register] + signed16(immediate & 0xFFFF)) & 0xFFFFFFFF


def register_state(values: Mapping[int, int]) -> int:
    """Build a stable Qt block state from known register values."""

    state = 0
    for register, value in sorted(values.items()):
        state = ((state * 16777619) ^ register ^ value) & 0x7FFFFFFF
    return state


def _computed_destination(
    mnemonic: str,
    operands: list[str],
    values: Mapping[int, int],
) -> int | None:
    if mnemonic == "lui" and len(operands) == 2:
        immediate = _number(operands[1])
        return None if immediate is None else (immediate & 0xFFFF) << 16
    if mnemonic in _IMMEDIATE_WRITERS and len(operands) == 3:
        source, immediate = _known(values, operands[1]), _number(operands[2])
        return _immediate_result(mnemonic, source, immediate)
    if mnemonic in _REGISTER_WRITERS and len(operands) == 3:
        return _register_result(mnemonic, _known(values, operands[1]), _known(values, operands[2]))
    if mnemonic in _SHIFT_IMMEDIATE_WRITERS and len(operands) == 3:
        source, shift = _known(values, operands[1]), _number(operands[2])
        return _shift_result(mnemonic, source, shift)
    if mnemonic in _SHIFT_VARIABLE_WRITERS and len(operands) == 3:
        source, shift = _known(values, operands[1]), _known(values, operands[2])
        return _shift_result(mnemonic[:-1], source, shift)
    if mnemonic == "move" and len(operands) == 2:
        return _known(values, operands[1])
    if mnemonic == "clear" and len(operands) == 1:
        return 0
    return None


def _immediate_result(mnemonic: str, source: int | None, immediate: int | None) -> int | None:
    if source is None or immediate is None:
        return None
    if mnemonic in {"addi", "addiu"}:
        return source + signed16(immediate & 0xFFFF)
    if mnemonic == "andi":
        return source & (immediate & 0xFFFF)
    if mnemonic == "ori":
        return source | (immediate & 0xFFFF)
    if mnemonic == "xori":
        return source ^ (immediate & 0xFFFF)
    signed_source = source - 0x100000000 if source & 0x80000000 else source
    comparison = signed_source < signed16(immediate & 0xFFFF) if mnemonic == "slti" else source < (immediate & 0xFFFF)
    return int(comparison)


def _register_result(mnemonic: str, left: int | None, right: int | None) -> int | None:
    if left is None or right is None:
        return None
    operations = {
        "add": left + right, "addu": left + right, "and": left & right,
        "nor": ~(left | right), "or": left | right, "slt": int(left < right),
        "sltu": int(left < right), "sub": left - right, "subu": left - right,
        "xor": left ^ right,
    }
    return operations[mnemonic]


def _shift_result(mnemonic: str, source: int | None, shift: int | None) -> int | None:
    if source is None or shift is None:
        return None
    amount = shift & 0x1F
    if mnemonic == "sll":
        return source << amount
    if mnemonic == "srl":
        return source >> amount
    signed_source = source - 0x100000000 if source & 0x80000000 else source
    return signed_source >> amount


def _writes_destination(mnemonic: str) -> bool:
    return mnemonic == "lui" or mnemonic in {
        *_IMMEDIATE_WRITERS, *_REGISTER_WRITERS, *_SHIFT_IMMEDIATE_WRITERS,
        *_SHIFT_VARIABLE_WRITERS, *_UNKNOWN_DESTINATION_WRITERS, "clear", "move",
    }


def _known(values: Mapping[int, int], token: str) -> int | None:
    register = _register_index(token)
    return values.get(register) if register is not None else None


def _register_index(token: str) -> int | None:
    return REGISTERS.get(token.strip().lower().lstrip("$"))


def _number(token: str) -> int | None:
    try:
        return int(token, 0)
    except ValueError:
        return None
