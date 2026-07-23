from pathlib import Path

import pytest

from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.debugger.directives.parser import parse_debugger_directives
from src.core.debugger.imports.source import DebuggerResolvedImport
from src.core.debugger.memory.builder import build_debugger_memory
from src.core.debugger.models.session import DebuggerError, DebuggerErrorCode
from src.core.debugger.psx_r3000a.debugger import BWDebuggerPSXR3000A
from src.core.debugger.psx_r3000a.registers import PsxR3000ARegisters
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)


def test_backend_rejects_access_inside_page_but_outside_declared_range():
    """Keep Unicorn page alignment from widening debugger-visible memory."""

    start, end = 0x1004, 0x1FFF
    data = PsxMipsR3000ACodec().assemble("lw $t0, 0x1000($zero)", start)
    assert data is not None
    document = parse_debugger_directives(
        [
            f"* virtual_memory_range 0x{start:X} 0x{end:X}",
            f"* define $pc 0x{start:X}",
        ]
    )
    imported = DebuggerResolvedImport(
        Path("boundary.asm"),
        None,
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        start,
        data,
        "boundary.asm",
        (),
    )
    image = build_debugger_memory(document, [imported], PsxR3000ARegisters())
    debugger = BWDebuggerPSXR3000A()
    debugger.configure_memory(image)

    with pytest.raises(DebuggerError) as captured:
        debugger.step()

    assert captured.value.code == DebuggerErrorCode.EXECUTION_FAILED
    invalid = next(event for event in debugger.events if event.details.get("pc") == start)
    assert invalid.address == 0x1000


def test_backend_executes_from_the_psx_cached_segment():
    """Translate `0x80000000` to physical memory without changing the PSX PC."""

    start, end = 0x80000000, 0x801DFFFF
    data = PsxMipsR3000ACodec().assemble("addiu $t0, $zero, 7", start)
    document = parse_debugger_directives(
        [
            f"* virtual_memory_range 0x{start:X} 0x{end:X}",
            "* define $sp 0x801FFFF0",
            f"* define $pc 0x{start:X}",
        ]
    )
    imported = DebuggerResolvedImport(
        Path("high.asm"),
        None,
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        start,
        data,
        "high.asm",
        (),
    )
    image = build_debugger_memory(document, [imported], PsxR3000ARegisters())
    debugger = BWDebuggerPSXR3000A()
    debugger.configure_memory(image)

    debugger.step()

    assert debugger.registers.read("t0") == 7
    assert debugger.pc == start + 4
