"""Exercise packaged Keystone and Unicorn through the reported JAL scenario."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from keystone import KS_ARCH_MIPS, KS_MODE_LITTLE_ENDIAN, KS_MODE_MIPS32, Ks

from src.core.debugger.directives.parser import parse_debugger_directives
from src.core.debugger.imports.source import DebuggerResolvedImport
from src.core.debugger.memory.builder import build_debugger_memory
from src.core.debugger.models.session import DebuggerInstruction, DebuggerSessionState
from src.core.debugger.psx_r3000a.debugger import BWDebuggerPSXR3000A
from src.core.debugger.psx_r3000a.registers import PsxR3000ARegisters
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)

SMOKE_BASE = 0x8000F800
SMOKE_INITIAL_PC = 0x8000F820
SMOKE_FINAL_PC = 0x8000F82C
SMOKE_EXPECTED_V0 = 0x801A7AD8
SMOKE_EXECUTION_LIMIT = 64
SMOKE_INSTRUCTIONS = (
    "sll $t0, $a0, 5",
    "sll $t1, $a0, 2",
    "subu $t0, $t0, $t1",
    "lui $v0, 0x801a",
    "ori $v0, $v0, 0x7ad8",
    "jr $ra",
    "addu $v0, $v0, $t0",
    "nop",
    "jal 0x8000f800",
    "addiu $a0, $zero, 0",
    "nop",
)
SMOKE_TRACE_ENVIRONMENT = "NUMERIC_WORKBENCH_SMOKE_TRACE"


@dataclass(frozen=True)
class DebuggerNativeSmokeResult:
    """Expose the final native execution state required by release builds."""

    pc: int
    v0: int
    state: DebuggerSessionState
    error: str | None


def create_debugger_native_smoke_session() -> BWDebuggerPSXR3000A:
    """Create the exact mapped JAL session that previously crashed builds."""

    _trace("create:keystone")
    engine = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 | KS_MODE_LITTLE_ENDIAN)
    chunks = tuple(
        _assemble_native(engine, instruction, SMOKE_BASE + index * 4)
        for index, instruction in enumerate(SMOKE_INSTRUCTIONS)
    )
    data = b"".join(chunks)
    _trace("create:assembled")
    document = parse_debugger_directives(
        (
            "* virtual_memory_range 0x80000000 0x801DFFFF",
            f"* import current_file 0x{SMOKE_BASE:08X}",
            "* define $sp 0x801FFF00",
            f"* define $pc 0x{SMOKE_INITIAL_PC:08X}",
            "* define $gp 0x8009AF08",
        )
    )
    _trace("create:directives")
    imported = DebuggerResolvedImport(
        Path("build_smoke.asm"),
        None,
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        SMOKE_BASE,
        data,
        "current_file",
        (),
    )
    image = build_debugger_memory(document, (imported,), PsxR3000ARegisters())
    _trace("create:memory-image")
    metadata = tuple(
        DebuggerInstruction(
            SMOKE_BASE + index * 4,
            chunk,
            instruction,
            "current_file",
        )
        for index, (chunk, instruction) in enumerate(zip(chunks, SMOKE_INSTRUCTIONS))
    )
    debugger = BWDebuggerPSXR3000A()
    _trace("create:debugger")
    debugger.configure_memory(image, metadata)
    _trace("create:configured")
    return debugger


def run_debugger_native_smoke() -> DebuggerNativeSmokeResult:
    """Execute and validate JAL, delay slot, return, registers, and completion."""

    debugger = create_debugger_native_smoke_session()
    debugger.run(limit=SMOKE_EXECUTION_LIMIT)
    return validate_debugger_native_smoke(debugger)


def validate_debugger_native_smoke(
    debugger: BWDebuggerPSXR3000A,
) -> DebuggerNativeSmokeResult:
    """Return a result or raise when the packaged native path is inconsistent."""

    result = DebuggerNativeSmokeResult(
        debugger.pc,
        debugger.registers.read("v0"),
        debugger.state,
        debugger.last_error.message if debugger.last_error else None,
    )
    expected = (SMOKE_FINAL_PC, SMOKE_EXPECTED_V0, DebuggerSessionState.STOPPED, None)
    if (result.pc, result.v0, result.state, result.error) != expected:
        raise RuntimeError(f"Debugger native smoke state is invalid: {result}")
    return result


def _assemble_native(engine: Ks, instruction: str, address: int) -> bytes:
    """Assemble one instruction through Keystone and require one MIPS word."""

    encoded, _count = engine.asm(instruction, address)
    data = bytes(encoded[:4])
    if len(data) != 4:
        raise RuntimeError(f"Keystone did not emit one MIPS word: {instruction}")
    return data


def trace_debugger_native_smoke(stage: str) -> None:
    """Record private build-smoke progress without affecting normal execution."""

    _trace(stage)


def _trace(stage: str) -> None:
    """Persist the last native boundary so a fail-fast build remains diagnosable."""

    destination = os.environ.get(SMOKE_TRACE_ENVIRONMENT, "")
    if not destination:
        return
    try:
        with Path(destination).open("a", encoding="utf-8") as stream:
            stream.write(f"{stage}\n")
    except OSError:
        pass
