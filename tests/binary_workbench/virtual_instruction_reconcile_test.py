from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.core.binary_workbench.virtual_instruction_reconcile import (
    reconcile_locked_virtual_instructions,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def test_locked_virtual_reconcile_replaces_repeated_nop_at_current_offset():
    rows = [
        BinaryWorkbenchRowDTO(
            offsets={"File": "0x00000000"},
            instruction="addiu $a0, $zero, 0x11",
            bytes_text="11 00 04 24",
        ),
        BinaryWorkbenchRowDTO(
            offsets={"File": "0x00000004"},
            instruction="nop",
            bytes_text="00 00 00 00",
        ),
        BinaryWorkbenchRowDTO(
            offsets={"File": "0x00000008"},
            instruction="addiu $a1, $zero, 0x12",
            bytes_text="12 00 05 24",
        ),
    ]

    updated = reconcile_locked_virtual_instructions(
        ["nop", rows[1].instruction, rows[2].instruction],
        rows,
        ["File"],
        {"File": "0x00000000"},
        PsxMipsR3000ACodec(),
        {},
        {},
        {},
    )

    assert [row.offsets["File"] for row in updated] == [
        "0x00000000",
        "0x00000004",
        "0x00000008",
    ]
    assert updated[0].instruction == "nop"
    assert updated[0].bytes_text == "00 00 00 00"
    assert updated[1].instruction == "nop"
    assert updated[2].instruction == rows[2].instruction