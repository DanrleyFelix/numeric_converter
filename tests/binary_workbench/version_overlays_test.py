from pathlib import Path

from src.core.binary_workbench.context_overlays import (
    compact_binary_context_overlays,
)
from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
    without_blank_instruction_overlays,
)
from src.modules.dtos import BinaryWorkbenchTabContextDTO


def test_blank_instruction_overlay_does_not_create_nop_bytes():
    assert byte_overlays_from_instruction_overlays({"0x00000000": ""}, {}, {}) == {}


def test_blank_instruction_overlay_removes_matching_persisted_bytes():
    assert without_blank_instruction_overlays(
        {"0x00000000": "00 00 00 00"},
        {"0x00000000": ""},
    ) == ({}, {})


def test_binary_context_compacts_redundant_rows_and_legacy_nop_corruption(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes.fromhex("00 00 00 00 01 02 03 04 00 00 00 00"))
    context = BinaryWorkbenchTabContextDTO(
        tab_id="binary",
        kind="binary",
        display_name=source.name,
        source_path=str(source),
        byte_overlays={"0x00000004": "00 00 00 00"},
        instruction_overlays={
            "0x00000000": "NOP",
            "0x00000004": "NOP",
            "0x00000008": "ADDIU $sp, $sp, -0x10",
        },
        version_dirty=True,
    )

    compacted = compact_binary_context_overlays(context)

    assert compacted.byte_overlays == {}
    assert compacted.instruction_overlays == {
        "0x00000008": "ADDIU $sp, $sp, -0x10"
    }
    assert compacted.version_dirty is True
