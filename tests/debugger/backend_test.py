from pathlib import Path

import pytest

from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.debugger import BWDebuggerPSXR3000A, DebuggerError, DebuggerErrorCode
from src.core.debugger.imports.source import DebuggerResolvedImport
from src.core.debugger.memory.builder import build_debugger_memory
from src.core.debugger.psx_r3000a.registers import PsxR3000ARegisters
from src.core.debugger.directives.parser import parse_debugger_directives
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)

BASE = 0x1000
END = 0x1FFF


def _assembled(*instructions: str) -> bytes:
    """Assemble a contiguous little-endian MIPS instruction sequence."""

    codec = PsxMipsR3000ACodec()
    output = bytearray()
    for index, instruction in enumerate(instructions):
        data = codec.assemble(instruction, BASE + index * 4)
        assert data is not None
        output.extend(data)
    return bytes(output)


def _debugger(data: bytes) -> BWDebuggerPSXR3000A:
    """Create a configured PSX debugger for one assembled sequence."""

    document = parse_debugger_directives(
        [
            f"* virtual_memory_range 0x{BASE:X} 0x{END:X}",
            f"* define $pc 0x{BASE:X}",
            f"* define $sp 0x{END - 3:X}",
        ]
    )
    imported = DebuggerResolvedImport(
        Path("test.asm"),
        None,
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        BASE,
        data,
        "test.asm",
        (),
    )
    image = build_debugger_memory(document, [imported], PsxR3000ARegisters())
    debugger = BWDebuggerPSXR3000A()
    debugger.configure_memory(image)
    return debugger


def test_unicorn_backend_executes_arithmetic_and_logic_instructions():
    debugger = _debugger(
        _assembled(
            "addiu $t0, $zero, 5",
            "addiu $t1, $t0, 3",
            "xor $t2, $t1, $t0",
        )
    )

    debugger.step()
    debugger.step()
    debugger.step()

    assert debugger.registers.read("t0") == 5
    assert debugger.registers.read("t1") == 8
    assert debugger.registers.read("t2") == 13


def test_unicorn_backend_executes_loads_and_stores():
    debugger = _debugger(
        _assembled(
            "addiu $t0, $zero, 0x1100",
            "addiu $t1, $zero, 0x1234",
            "sw $t1, 0($t0)",
            "lw $t2, 0($t0)",
            "nop",
        )
    )

    for _ in range(5):
        debugger.step()

    assert debugger.read_memory(0x1100, 4) == b"\x34\x12\x00\x00"
    assert debugger.registers.read("t2") == 0x1234


def test_unicorn_backend_preserves_branch_delay_slot_semantics():
    debugger = _debugger(
        _assembled(
            "beq $zero, $zero, 0x0001",
            "addiu $t0, $zero, 1",
            "addiu $t1, $zero, 2",
        )
    )

    debugger.step()
    assert debugger.registers.read("t0") == 1
    assert debugger.pc == BASE + 8
    debugger.step()

    assert debugger.registers.read("t1") == 2
    assert debugger.pc == BASE + 12


def test_unicorn_backend_executes_jal_and_sets_return_address():
    debugger = _debugger(
        _assembled(
            f"jal 0x{BASE + 0x10:X}",
            "nop",
            "nop",
            "nop",
            "addiu $v0, $zero, 7",
        )
    )

    debugger.step()
    debugger.step()

    assert debugger.registers.read("ra") == BASE + 8
    assert debugger.registers.read("v0") == 7


def test_unicorn_backend_executes_jalr_with_its_delay_slot():
    debugger = _debugger(
        _assembled(
            f"addiu $t0, $zero, 0x{BASE + 0x10:X}",
            "jalr $ra, $t0",
            "addiu $a0, $zero, 3",
            "nop",
            "addiu $v0, $zero, 9",
        )
    )

    debugger.step()
    debugger.step()
    debugger.step()

    assert debugger.registers.read("ra") == BASE + 12
    assert debugger.registers.read("a0") == 3
    assert debugger.registers.read("v0") == 9


def test_unicorn_failures_are_converted_to_controlled_debugger_errors():
    debugger = _debugger(_assembled("nop"))
    debugger.pc = END + 1

    with pytest.raises(DebuggerError) as captured:
        debugger.step()

    assert captured.value.code == DebuggerErrorCode.INVALID_MEMORY
    assert debugger.last_error is captured.value
