from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.binary_workbench.persistence import normalize_locked_assembly_rows
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def test_locked_assembly_restores_valid_bytes_and_retains_invalid_attempt():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": "0x00000000"},
            "bad $a0 ; keep this",
            "00 00 00 00",
        ),
        BinaryWorkbenchRowDTO(
            {"File": "0x00000004"},
            "entry: invalid_target",
            "02 00 84 24",
        ),
        BinaryWorkbenchRowDTO(
            {"File": "-"},
            "* define $sp 0x801FFFF0",
            "",
        ),
    ]

    normalized = normalize_locked_assembly_rows(
        rows,
        binary_workbench_codec_for(BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME),
        {},
        {},
        {},
    )

    assert normalized[0].instruction == (
        "nop; Incorrect Instruction: bad $a0 | keep this"
    )
    assert normalized[1].instruction == (
        "entry: addiu $a0, $a0, 0x2; Incorrect Instruction: invalid_target"
    )
    assert normalized[0].bytes_text == "00 00 00 00"
    assert normalized[1].bytes_text == "02 00 84 24"
    assert normalized[2] == rows[2]


def test_locked_assembly_uses_previous_version_bytes_when_projection_is_empty():
    attempted = [
        BinaryWorkbenchRowDTO({"File": "0x00000000"}, "", ""),
    ]
    previous = [
        BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
    ]

    normalized = normalize_locked_assembly_rows(
        attempted,
        binary_workbench_codec_for(BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME),
        {},
        {},
        {},
        (previous,),
    )

    assert normalized[0].instruction == (
        "nop; Incorrect Instruction: <empty>"
    )
    assert normalized[0].bytes_text == "00 00 00 00"


def test_locked_assembly_preserves_previous_source_label_and_comment():
    attempted = [
        BinaryWorkbenchRowDTO({"File": "0x00000000"}, "", "00 00 00 00"),
    ]
    previous = [
        BinaryWorkbenchRowDTO(
            {"File": "0x00000000"},
            "entry: nop; previous context",
            "00 00 00 00",
        ),
    ]

    normalized = normalize_locked_assembly_rows(
        attempted,
        binary_workbench_codec_for(BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME),
        {},
        {},
        {},
        (previous,),
    )

    assert normalized[0].instruction == (
        "entry: nop; Incorrect Instruction: <empty> | previous context"
    )
