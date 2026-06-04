from src.core.binary_workbench.text_search import ansi_text_bytes, find_bytes_in_rows
from src.modules.dtos import BinaryWorkbenchRowDTO


def test_ansi_text_bytes_uses_windows_ansi_encoding():
    assert ansi_text_bytes("ação") == b"a\xe7\xe3o"


def test_find_bytes_in_rows_respects_optional_offset_range():
    rows = [
        BinaryWorkbenchRowDTO({"File": "0x00000000"}, "", "00 48 45 4C"),
        BinaryWorkbenchRowDTO({"File": "0x00000004"}, "", "4C 4F 00 48"),
        BinaryWorkbenchRowDTO({"File": "0x00000008"}, "", "45 4C 4C 4F"),
    ]

    assert find_bytes_in_rows(rows, b"HELLO") == [1, 7]
    assert find_bytes_in_rows(rows, b"HELLO", start_offset=1, end_offset=5) == [1]
    assert find_bytes_in_rows(rows, b"HELLO", start_offset=7) == [7]
    assert find_bytes_in_rows(rows, b"HELLO", end_offset=5) == [1]
