from __future__ import annotations

from dataclasses import dataclass

from src.core.debugger.psx_r3000a.registers import GPR_NAMES


@dataclass(frozen=True)
class PsxControlFlow:
    """Describe a decoded R3000A jump or call destination."""

    mnemonic: str
    destination: int
    is_call: bool


def decode_control_flow(
    data: bytes,
    pc: int,
    registers: dict[str, int],
) -> PsxControlFlow | None:
    """Decode direct and register R3000A control-flow instructions."""

    if len(data) != 4:
        return None
    word = int.from_bytes(data, "little")
    opcode = word >> 26
    if opcode in {2, 3}:
        destination = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        return PsxControlFlow("jal" if opcode == 3 else "j", destination, opcode == 3)
    if opcode != 0:
        return None
    function = word & 0x3F
    if function not in {8, 9}:
        return None
    register_index = (word >> 21) & 0x1F
    destination = registers.get(GPR_NAMES[register_index], 0)
    mnemonic = "jalr" if function == 9 else "jr"
    return PsxControlFlow(mnemonic, destination, function == 9)
