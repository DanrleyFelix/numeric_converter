from pathlib import Path

from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.debugger.directives.parser import parse_debugger_directives
from src.core.debugger.imports.source import DebuggerResolvedImport
from src.core.debugger.memory.builder import build_debugger_memory
from src.core.debugger.models.session import DebuggerInstruction
from src.core.debugger.psx_r3000a.debugger import BWDebuggerPSXR3000A
from src.core.debugger.psx_r3000a.registers import PsxR3000ARegisters
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)

BASE = 0x1000
END = 0x1FFF


def configured_debugger(*instructions: str, ignored: tuple[int, ...] = ()):
    """Create a debugger with metadata for execution-control tests."""

    codec = PsxMipsR3000ACodec()
    chunks = [codec.assemble(text, BASE + index * 4) for index, text in enumerate(instructions)]
    assert all(chunk is not None for chunk in chunks)
    data = b"".join(chunks)
    lines = [
        f"* virtual_memory_range 0x{BASE:X} 0x{END:X}",
        f"* define $pc 0x{BASE:X}",
        f"* define $sp 0x{END - 3:X}",
        *(f"* ignore $pc 0x{address:X}" for address in ignored),
    ]
    document = parse_debugger_directives(lines)
    imported = DebuggerResolvedImport(
        Path("control.asm"),
        None,
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        BASE,
        data,
        "control.asm",
        (),
    )
    image = build_debugger_memory(document, [imported], PsxR3000ARegisters())
    metadata = tuple(
        DebuggerInstruction(BASE + index * 4, chunk, text, "control.asm")
        for index, (chunk, text) in enumerate(zip(chunks, instructions))
    )
    debugger = BWDebuggerPSXR3000A()
    debugger.configure_memory(image, metadata)
    return debugger
