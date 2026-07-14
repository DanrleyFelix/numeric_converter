from src.core.binary_workbench.byte_replacement import (
    bytes_from_rows,
    merged_byte_overlays,
    parse_replace_bytes_request,
    replaced_row_byte_lines,
    without_overlapping_instructions,
)
from src.core.binary_workbench.byte_replacement_growth import (
    replaced_or_extended_row_byte_lines,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def test_replace_bytes_request_parses_multiline_bytes_and_safety_limits():
    request = parse_replace_bytes_request(
        "0x20",
        "2F",
        "0x10",
        "AA BB\nCC DD",
    )

    assert request is not None
    assert request.start_offset == 0x20
    assert request.end_offset == 0x2F
    assert request.length_limit == 0x10
    assert request.data == bytes.fromhex("AA BB CC DD")
    assert parse_replace_bytes_request("20", "22", "", "AA BB CC DD") is None
    assert parse_replace_bytes_request("20", "", "3", "AA BB CC DD") is None


def test_replace_bytes_reads_and_updates_exact_row_range():
    rows = [
        BinaryWorkbenchRowDTO(offsets={"File": "0x00000000"}, bytes_text="00 01 02 03"),
        BinaryWorkbenchRowDTO(offsets={"File": "-"}, bytes_text=""),
        BinaryWorkbenchRowDTO(offsets={"File": "0x00000004"}, bytes_text="04 05 06 07"),
    ]

    assert bytes_from_rows(rows, 2, 4) == bytes.fromhex("02 03 04 05")
    assert replaced_row_byte_lines(rows, 2, bytes.fromhex("AA BB CC DD")) == [
        "00 01 AA BB",
        "",
        "CC DD 06 07",
    ]


def test_replace_bytes_extends_rows_only_when_structural_growth_is_allowed():
    rows = [
        BinaryWorkbenchRowDTO(offsets={"File": "0x00000000"}, bytes_text="00 01 02 03"),
        BinaryWorkbenchRowDTO(offsets={"File": "0x00000004"}, bytes_text="04 05"),
    ]
    replacement = bytes.fromhex("AA BB CC DD 11 22")

    assert replaced_or_extended_row_byte_lines(rows, 4, replacement, False) is None
    assert replaced_or_extended_row_byte_lines(rows, 4, replacement, True) == [
        "00 01 02 03",
        "AA BB CC DD",
        "11 22",
    ]

def test_replace_bytes_merges_overlays_and_discards_overlapping_instructions():
    overlays = {
        "0x00000000": "10 11 12 13 14 15 16 17",
        "0x0000000C": "CC DD",
    }

    assert merged_byte_overlays(overlays, 2, bytes.fromhex("AA BB CC DD")) == {
        "0x00000000": "10 11",
        "0x00000002": "AA BB CC DD",
        "0x00000006": "16 17",
        "0x0000000C": "CC DD",
    }
    assert without_overlapping_instructions(
        {"0x00000000": "nop", "0x00000004": "nop", "0x00000008": "nop"},
        2,
        4,
    ) == {"0x00000008": "nop"}
