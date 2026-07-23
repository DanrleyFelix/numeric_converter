from pathlib import Path

import pytest

from src.core.debugger import DebuggerError, DebuggerErrorCode, parse_debugger_directives
from src.core.debugger.imports.source import DebuggerResolvedImport
from src.core.debugger.memory.builder import build_debugger_memory
from src.core.debugger.psx_r3000a.registers import PsxR3000ARegisters
from src.core.debugger.psx_r3000a.debugger import BWDebuggerPSXR3000A
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)


def _import(name: str, address: int, data: bytes) -> DebuggerResolvedImport:
    """Create one resolved import for virtual-memory tests."""

    return DebuggerResolvedImport(
        Path(name),
        f"{name}.workspace.json",
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        address,
        data,
        name,
        (),
    )


def _document(*extra: str):
    """Parse a small valid main source with optional directives."""

    return parse_debugger_directives(
        [
            "* virtual_memory_range 0x80000000 0x800000FF",
            *extra,
            "* define $pc 0x80000010",
        ]
    )


def test_memory_builder_creates_zero_filled_snapshot_zones_and_registers():
    document = _document("* define $sp 0x800000F0")
    imported = _import("main.asm", 0x80000010, b"\x01\x02\x03\x04")

    image = build_debugger_memory(document, [imported], PsxR3000ARegisters())

    assert image.size == 0x100
    assert image.data[0x10:0x14] == b"\x01\x02\x03\x04"
    assert image.data[:0x10] == bytes(0x10)
    assert image.initial_snapshot is image.data
    assert image.initial_registers["pc"] == 0x80000010
    assert image.initial_registers["sp"] == 0x800000F0
    assert image.initial_registers["v0"] == 0
    assert image.zones[0].loaded_bytes == 4
    assert image.zones[0].end == 0x80000013


def test_memory_builder_keeps_last_import_and_records_real_overlap():
    imports = [
        _import("first.asm", 0x80000010, b"\x11" * 8),
        _import("second.asm", 0x80000014, b"\x22" * 8),
    ]

    image = build_debugger_memory(_document(), imports, PsxR3000ARegisters())

    assert image.data[0x10:0x14] == b"\x11" * 4
    assert image.data[0x14:0x1C] == b"\x22" * 8
    assert len(image.overlaps) == 1
    assert image.overlaps[0].first_origin == "first.asm"
    assert image.overlaps[0].second_origin == "second.asm"
    assert image.overlaps[0].size == 4
    debugger = BWDebuggerPSXR3000A()
    debugger.configure_memory(image)
    warnings = [event for event in debugger.events if event.level == "Warning"]
    assert len(warnings) == 1
    assert sum("Import loaded:" in event.message for event in debugger.events) == 2
    assert any("Virtual memory range:" in event.message for event in debugger.events)


def test_memory_builder_clips_out_of_range_bytes_and_rejects_unmapped_pc():
    outside = _import("outside.asm", 0x800000FC, bytes(range(8)))
    unmapped = _import("other.asm", 0x80000020, bytes(4))

    image = build_debugger_memory(_document(), [outside, _import("pc.asm", 0x80000010, bytes(4))], PsxR3000ARegisters())
    assert image.data[-4:] == bytes(range(4))
    assert image.zones[0].loaded_bytes == 4
    with pytest.raises(DebuggerError, match="initial PC"):
        build_debugger_memory(_document(), [unmapped], PsxR3000ARegisters())


def test_memory_builder_records_ignored_addresses():
    document = _document("* ignore $pc 0x80000080")

    image = build_debugger_memory(
        document,
        [_import("main.asm", 0x80000010, bytes(4))],
        PsxR3000ARegisters(),
    )

    assert image.ignored_addresses == frozenset({0x80000080})
