from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.core.debugger.psx_r3000a.registers import GPR_NAMES


def decode_branch(
    word: int,
    opcode: int,
    pc: int,
    registers: dict[str, int],
    control_factory: Callable[..., Any],
) -> Any | None:
    """Decode a conditional branch without coupling to its result dataclass."""

    rs = _signed(registers.get(GPR_NAMES[(word >> 21) & 0x1F], 0))
    rt = _signed(registers.get(GPR_NAMES[(word >> 16) & 0x1F], 0))
    mnemonic = ""
    taken = False
    is_call = False
    if opcode == 1:
        variant = (word >> 16) & 0x1F
        variants = {
            0: ("bltz", rs < 0),
            1: ("bgez", rs >= 0),
            16: ("bltzal", rs < 0),
            17: ("bgezal", rs >= 0),
        }
        if variant not in variants:
            return None
        mnemonic, taken = variants[variant]
        is_call = variant in {16, 17}
    elif opcode == 4:
        mnemonic, taken = "beq", rs == rt
    elif opcode == 5:
        mnemonic, taken = "bne", rs != rt
    elif opcode == 6:
        mnemonic, taken = "blez", rs <= 0
    elif opcode == 7:
        mnemonic, taken = "bgtz", rs > 0
    else:
        return None
    immediate = word & 0xFFFF
    immediate -= 0x10000 if immediate & 0x8000 else 0
    destination = (pc + 4 + (immediate << 2)) & 0xFFFFFFFF
    return control_factory(mnemonic, destination, is_call, "branch", taken)


def _signed(value: int) -> int:
    """Interpret one register value as a signed 32-bit integer."""

    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value
