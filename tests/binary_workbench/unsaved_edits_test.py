from src.modules.binary_workbench_use_cases import (
    binary_version_has_unsaved_edits,
    rows_have_meaningful_edits,
)
from src.modules.dtos import (
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
)


def test_binary_version_dirty_flag_ignores_whitespace_only_overlays():
    context = BinaryWorkbenchTabContextDTO(
        tab_id="binary",
        kind="binary",
        display_name="source.bin",
        byte_overlays={"0x00000000": "00 00 00 00"},
        instruction_overlays={"0x00000000": "\t"},
        version_dirty=True,
    )

    assert binary_version_has_unsaved_edits(context) is False


def test_binary_version_dirty_flag_alone_does_not_mark_changes():
    context = BinaryWorkbenchTabContextDTO(
        tab_id="binary",
        kind="binary",
        display_name="source.bin",
        active_version_name="v1",
        versions=[BinaryWorkbenchVersionDTO("v1")],
        version_dirty=True,
    )

    assert binary_version_has_unsaved_edits(context) is False


def test_binary_version_detects_removed_saved_overlay():
    context = BinaryWorkbenchTabContextDTO(
        tab_id="binary",
        kind="binary",
        display_name="source.bin",
        active_version_name="v1",
        versions=[
            BinaryWorkbenchVersionDTO(
                "v1",
                rows=[
                    BinaryWorkbenchRowDTO(
                        offsets={"File": "0x00000000"},
                        bytes_text="AA BB CC DD",
                    )
                ],
            )
        ],
        version_dirty=True,
    )

    assert binary_version_has_unsaved_edits(context) is True


def test_rows_ignore_whitespace_only_lines_but_keep_real_characters():
    original = [BinaryWorkbenchRowDTO(instruction="NOP", bytes_text="00 00 00 00")]
    rows = [
        BinaryWorkbenchRowDTO(instruction=" NOP ", bytes_text="00 00 00 00"),
        BinaryWorkbenchRowDTO(instruction="   ", bytes_text=""),
    ]

    assert rows_have_meaningful_edits(rows, original) is False
    rows.append(BinaryWorkbenchRowDTO(instruction="; comment", bytes_text=""))
    assert rows_have_meaningful_edits(rows, original) is True
