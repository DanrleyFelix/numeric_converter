from pathlib import Path

from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.debugger.backends.memory.mapping import unicorn_memory_address
from src.core.debugger.directives.parser import parse_debugger_directives
from src.core.debugger.imports.source import DebuggerResolvedImport
from src.core.debugger.memory.builder import build_debugger_memory
from src.core.debugger.models.session import DebuggerSessionState
from src.core.debugger.psx_r3000a.debugger import BWDebuggerPSXR3000A
from src.core.debugger.psx_r3000a.registers import PsxR3000ARegisters
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)

BASE = 0x80000000
END = 0x801DFFFF
INITIAL_SP = 0x801FFFF0
ACTIVE_SP = 0x801FFF90
STACK_REGISTERS = (
    "a0", "a1", "a2", "a3", "v0", "v1",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9",
)
STACK_SEQUENCE = (
    "addiu $sp, $sp, -0x60",
    *(f"sw ${name}, 0x{index * 4:X}($sp)" for index, name in enumerate(STACK_REGISTERS)),
    *(f"lw ${name}, 0x{index * 4:X}($sp)" for index, name in enumerate(STACK_REGISTERS)),
    "addiu $sp, $sp, 0x60",
)


def _stack_debugger() -> BWDebuggerPSXR3000A:
    """Build the exact requested stack sequence at the PSX cached segment."""

    codec = PsxMipsR3000ACodec()
    chunks = [codec.assemble(text, BASE + index * 4) for index, text in enumerate(STACK_SEQUENCE)]
    assert all(chunk is not None for chunk in chunks)
    document = parse_debugger_directives(
        [
            f"* virtual_memory_range 0x{BASE:X} 0x{END:X}",
            f"* define $sp 0x{INITIAL_SP:X}",
            f"* define $pc 0x{BASE:X}",
        ]
    )
    imported = DebuggerResolvedImport(
        Path("stack.asm"),
        None,
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        BASE,
        b"".join(chunks),
        "stack.asm",
        (),
    )
    image = build_debugger_memory(document, [imported], PsxR3000ARegisters())
    debugger = BWDebuggerPSXR3000A()
    debugger.configure_memory(image)
    return debugger


def test_stack_sequence_preserves_kseg_address_and_all_register_values():
    """Execute all requested stores and loads without false physical-address errors."""

    debugger = _stack_debugger()
    expected = {name: index + 1 for index, name in enumerate(STACK_REGISTERS)}
    assert debugger.registers.read("sp") == INITIAL_SP
    assert debugger._image is not None and debugger._image.contains(ACTIVE_SP, 0x60)
    assert unicorn_memory_address(ACTIVE_SP) == 0x001FFF90
    for name, value in expected.items():
        debugger.registers.write(name, value)
    for _ in range(1 + len(STACK_REGISTERS)):
        debugger.step()
    assert debugger.registers.read("sp") == ACTIVE_SP
    for index, value in enumerate(expected.values()):
        assert debugger.read_memory(ACTIVE_SP + index * 4, 4) == value.to_bytes(4, "little")
    for name in STACK_REGISTERS:
        debugger.registers.write(name, 0)
    for _ in range(len(STACK_REGISTERS) + 1):
        debugger.step()
    assert debugger.registers.read("sp") == INITIAL_SP
    assert debugger.pc == BASE + len(STACK_SEQUENCE) * 4 == 0x800000C8
    assert debugger.state == DebuggerSessionState.STOPPED
    assert {name: debugger.registers.read(name) for name in STACK_REGISTERS} == expected
    assert not any(event.level == "Error" for event in debugger.events)
    stack_events = [event for event in debugger.events if event.address == ACTIVE_SP]
    assert stack_events and all("0x801FFF90" in event.message for event in stack_events)
