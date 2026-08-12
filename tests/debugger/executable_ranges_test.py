from pathlib import Path

from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.debugger.directives.parser import parse_debugger_directives
from src.core.debugger.imports.source import DebuggerResolvedImport
from src.core.debugger.memory.builder import build_debugger_memory
from src.core.debugger.models.session import DebuggerInstruction, DebuggerSessionState
from src.core.debugger.psx_r3000a.debugger import BWDebuggerPSXR3000A
from src.core.debugger.psx_r3000a.execution.ranges import build_executable_ranges
from src.core.debugger.psx_r3000a.registers import PsxR3000ARegisters
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)

ENTRY = 0x1000
IMPORTED = 0x1800
END = 0x1FFF


def _debugger(
    entry: tuple[str, ...],
    imported: tuple[str, ...] = (),
    *,
    initial_pc: int = ENTRY,
) -> BWDebuggerPSXR3000A:
    """Create separated executable ranges without involving presentation state."""

    codec = PsxMipsR3000ACodec()
    groups = ((ENTRY, "entry.asm", entry), (IMPORTED, "imported.asm", imported))
    resolved: list[DebuggerResolvedImport] = []
    metadata: list[DebuggerInstruction] = []
    for base, origin, instructions in groups:
        chunks = tuple(
            codec.assemble(text, base + index * 4)
            for index, text in enumerate(instructions)
        )
        assert all(chunk is not None for chunk in chunks)
        if not chunks:
            continue
        resolved.append(
            DebuggerResolvedImport(
                Path(origin),
                None,
                BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
                base,
                b"".join(chunks),
                origin,
                (),
            )
        )
        metadata.extend(
            DebuggerInstruction(base + index * 4, chunk, text, origin)
            for index, (chunk, text) in enumerate(zip(chunks, instructions))
        )
    document = parse_debugger_directives(
        (
            f"* virtual_memory_range 0x{ENTRY:X} 0x{END:X}",
            f"* define $pc 0x{initial_pc:X}",
            f"* define $sp 0x{END - 3:X}",
        )
    )
    image = build_debugger_memory(document, resolved, PsxR3000ARegisters())
    debugger = BWDebuggerPSXR3000A()
    debugger.configure_memory(image, tuple(metadata))
    return debugger


def test_return_from_distant_import_completes_at_entry_range_end():
    debugger = _debugger(
        (f"jal 0x{IMPORTED:X}", "nop", "nop"),
        ("jr $ra", "nop"),
    )

    debugger.run(limit=20)

    assert debugger.state == DebuggerSessionState.STOPPED
    assert debugger.pc == ENTRY + 12
    assert debugger.events[-1].message == f"Execution completed at 0x{ENTRY + 12:08X}."


def test_return_from_distant_import_completes_through_individual_steps():
    debugger = _debugger(
        (f"jal 0x{IMPORTED:X}", "nop", "nop"),
        ("jr $ra", "nop"),
    )

    for _ in range(10):
        debugger.step()
        if debugger.state == DebuggerSessionState.STOPPED:
            break

    assert debugger.state == DebuggerSessionState.STOPPED
    assert debugger.pc == ENTRY + 12


def test_step_over_returns_to_entry_then_naturally_completes():
    debugger = _debugger(
        (f"jal 0x{IMPORTED:X}", "nop", "nop"),
        ("jr $ra", "nop"),
    )

    debugger.step_over(limit=10)

    assert debugger.state == DebuggerSessionState.PAUSED
    assert debugger.pc == ENTRY + 8
    debugger.step()
    assert debugger.state == DebuggerSessionState.STOPPED
    assert debugger.pc == ENTRY + 12


def test_initial_pc_uses_the_import_range_as_its_entry_range():
    debugger = _debugger(("nop",), ("nop",), initial_pc=IMPORTED)

    debugger.run(limit=2)

    assert debugger.state == DebuggerSessionState.STOPPED
    assert debugger.pc == IMPORTED + 4


def test_import_fallthrough_without_return_remains_an_error():
    debugger = _debugger((f"jal 0x{IMPORTED:X}", "nop", "nop"), ("nop",))

    debugger.run(limit=10)

    assert debugger.state == DebuggerSessionState.ERROR
    assert debugger.pc == IMPORTED + 4


def test_call_or_taken_branch_to_entry_end_is_not_completion():
    scenarios = (
        (f"jal 0x{ENTRY + 12:X}", "nop", "nop"),
        ("beq $zero, $zero, 2", "nop", "nop"),
    )
    for instructions in scenarios:
        debugger = _debugger(instructions)

        debugger.run(limit=10)

        assert debugger.state == DebuggerSessionState.ERROR
        assert debugger.pc == ENTRY + 12


def test_branch_fallthrough_may_complete_the_entry_range():
    debugger = _debugger(("bne $zero, $zero, 1", "nop"))

    debugger.run(limit=10)

    assert debugger.state == DebuggerSessionState.STOPPED
    assert debugger.pc == ENTRY + 8


def test_adjacent_origins_remain_distinct_executable_ranges():
    instructions = (
        DebuggerInstruction(ENTRY, b"\x00\x00\x00\x00", "nop", "entry.asm"),
        DebuggerInstruction(ENTRY + 4, b"\x00\x00\x00\x00", "nop", "other.asm"),
    )

    ranges = build_executable_ranges(instructions)

    assert tuple((item.start, item.end_exclusive, item.origin) for item in ranges) == (
        (ENTRY, ENTRY + 4, "entry.asm"),
        (ENTRY + 4, ENTRY + 8, "other.asm"),
    )
