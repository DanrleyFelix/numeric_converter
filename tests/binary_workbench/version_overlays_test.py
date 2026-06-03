from pathlib import Path

from src.core.binary_workbench.context_overlays import (
    compact_binary_context_overlays,
)
from src.core.binary_workbench.legacy_overlays import discard_legacy_nop_overlays
from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.core.binary_workbench.symbolic_instructions import preserve_symbolic_rows
from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
    without_blank_instruction_overlays,
)
from src.modules.dtos import BinaryWorkbenchTabContextDTO, BinaryWorkbenchVersionDTO


def test_blank_instruction_overlay_does_not_create_nop_bytes():
    assert byte_overlays_from_instruction_overlays({"0x00000000": ""}, {}, {}) == {}


def test_blank_instruction_overlay_removes_matching_persisted_bytes():
    assert without_blank_instruction_overlays(
        {"0x00000000": "00 00 00 00"},
        {"0x00000000": ""},
    ) == ({}, {})


def test_binary_context_compacts_redundant_rows_and_discards_legacy_first_nop(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes.fromhex("00 FF FF FF 01 02 03 04 00 00 00 00"))
    context = BinaryWorkbenchTabContextDTO(
        tab_id="binary",
        kind="binary",
        display_name=source.name,
        source_path=str(source),
        byte_overlays={
            "0x00000000": "00 00 00 00",
            "0x00000004": "00 00 00 00",
        },
        instruction_overlays={
            "0x00000000": "NOP",
            "0x00000004": "NOP",
            "0x00000008": "ADDIU $sp, $sp, -0x10",
        },
        active_version_name="v1",
        versions=[BinaryWorkbenchVersionDTO("v1")],
        version_dirty=True,
    )

    compacted = discard_legacy_nop_overlays(compact_binary_context_overlays(context))

    assert compacted.byte_overlays == {"0x00000004": "00 00 00 00"}
    assert compacted.instruction_overlays == {
        "0x00000004": "NOP",
        "0x00000008": "ADDIU $sp, $sp, -0x10"
    }
    assert compacted.version_dirty is True


def test_legacy_cleanup_preserves_nop_saved_in_active_version(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes.fromhex("00 FF FF FF"))
    context = BinaryWorkbenchTabContextDTO(
        tab_id="binary",
        kind="binary",
        display_name=source.name,
        source_path=str(source),
        active_version_name="v1",
        versions=[
            BinaryWorkbenchVersionDTO(
                "v1",
                instruction_overlays={"0x00000000": "NOP"},
            )
        ],
        byte_overlays={"0x00000000": "00 00 00 00"},
        instruction_overlays={"0x00000000": "NOP"},
        version_dirty=True,
    )

    cleaned = discard_legacy_nop_overlays(context)

    assert cleaned.byte_overlays == {"0x00000000": "00 00 00 00"}
    assert cleaned.instruction_overlays == {"0x00000000": "NOP"}


def test_legacy_cleanup_preserves_nop_without_active_version(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes.fromhex("00 FF FF FF"))
    context = BinaryWorkbenchTabContextDTO(
        tab_id="binary",
        kind="binary",
        display_name=source.name,
        source_path=str(source),
        byte_overlays={"0x00000000": "00 00 00 00"},
        instruction_overlays={"0x00000000": "NOP"},
        version_dirty=True,
    )

    assert discard_legacy_nop_overlays(context) == context


def test_symbolic_preservation_ignores_rows_without_offsets():
    row = BinaryWorkbenchRowDTO(
        offsets={"File": "-"},
        instruction="; comment",
        bytes_text="AA BB CC DD",
    )
    previous = BinaryWorkbenchRowDTO(
        offsets={"File": "-"},
        instruction="; comment",
        bytes_text="",
    )

    assert preserve_symbolic_rows(
        [row],
        [previous],
        {},
        {},
        {},
        PsxMipsR3000ACodec(),
    ) == [row]


def test_symbolic_preservation_clears_rows_without_complete_bytes():
    row = BinaryWorkbenchRowDTO(
        offsets={"File": "-"},
        instruction="",
        bytes_text="",
    )
    previous = BinaryWorkbenchRowDTO(
        offsets={"File": "-"},
        instruction="; comment",
        bytes_text="",
    )

    assert preserve_symbolic_rows(
        [row],
        [previous],
        {},
        {},
        {},
        PsxMipsR3000ACodec(),
    ) == [row]
