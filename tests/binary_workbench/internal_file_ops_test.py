from pathlib import Path

from src.core.binary_workbench.file_ops import (
    build_internal_version_rows_from_overlay,
)
from src.core.binary_workbench.psx_sector_io import rebuild_psx_sector, save_internal_versioned_binary
from src.core.binary_workbench.psx_sector_layout import (
    RAW_SECTOR_SIZE,
    SYNC_HEADER,
    extract_internal_file_bytes,
    sector_layout,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO, BinaryWorkbenchRowDTO


def test_extract_internal_file_returns_only_mode2_form1_payload(tmp_path: Path):
    payloads = [bytes([value]) * 2048 for value in (0x11, 0x22, 0x33)]
    source = tmp_path / "disc.bin"
    source.write_bytes(b"".join(_mode2_form1_sector(data, index) for index, data in enumerate(payloads)))
    files = [BinaryWorkbenchInternalFileDTO("FIRST", 0), BinaryWorkbenchInternalFileDTO("NEXT", 2)]

    extracted = extract_internal_file_bytes(source, files[0], files, RAW_SECTOR_SIZE)

    assert extracted == payloads[0] + payloads[1]


def test_internal_version_rows_store_internal_binary_and_original_values(tmp_path: Path):
    source = tmp_path / "disc.bin"
    source.write_bytes(_mode2_form1_sector(bytes(2048), 0) + _mode2_form1_sector(bytes(2048), 1))
    files = [BinaryWorkbenchInternalFileDTO("FILE", 0)]
    original = [
        BinaryWorkbenchRowDTO(offsets={"File": "0x00000000"}, instruction="nop", bytes_text="00 00 00 00"),
        BinaryWorkbenchRowDTO(offsets={"File": "0x00000800"}, instruction="nop", bytes_text="00 00 00 00"),
    ]
    current = [
        BinaryWorkbenchRowDTO(offsets={"File": "0x00000000"}, instruction="jr $ra", bytes_text="08 00 E0 03"),
        BinaryWorkbenchRowDTO(offsets={"File": "0x00000800"}, instruction="nop", bytes_text="01 02 03 04"),
    ]

    rows = build_internal_version_rows_from_overlay(
        source,
        0,
        files,
        RAW_SECTOR_SIZE,
        {"0x00000000": "08 00 E0 03", "0x00000800": "01 02 03 04"},
        ["File"],
        {"File": "0x00000000"},
        original,
        current,
    )

    assert [row.offsets for row in rows] == [
        {"File": "0x00000000", "Binary": "0x00000018"},
        {"File": "0x00000800", "Binary": "0x00000948"},
    ]
    assert rows[0].original_bytes_text == "00 00 00 00"
    assert rows[0].original_instruction == "nop"
    assert rows[0].instruction == "jr $ra"


def test_save_internal_file_rebuilds_only_affected_sector(tmp_path: Path):
    source = tmp_path / "disc.bin"
    output = tmp_path / "patched.bin"
    first = _mode2_form1_sector(bytes(2048), 0)
    second = _mode2_form1_sector(bytes([0x55]) * 2048, 1)
    source.write_bytes(first + second)
    row = BinaryWorkbenchRowDTO(
        offsets={"File": "0x00000000", "Binary": "0x00000018"},
        bytes_text="DE AD BE EF",
    )

    save_internal_versioned_binary(source, output, [row], RAW_SECTOR_SIZE)

    saved = output.read_bytes()
    assert saved[24:28] == bytes.fromhex("DE AD BE EF")
    assert saved[RAW_SECTOR_SIZE:] == second
    assert saved[:RAW_SECTOR_SIZE] == rebuild_psx_sector(saved[:RAW_SECTOR_SIZE], 0)
    assert saved[:RAW_SECTOR_SIZE] != first


def test_sector_layout_recognizes_mode1_and_mode2_form2():
    mode1 = bytearray(RAW_SECTOR_SIZE)
    mode1[:12] = SYNC_HEADER
    mode1[15] = 1
    form2 = bytearray(RAW_SECTOR_SIZE)
    form2[:12] = SYNC_HEADER
    form2[15] = 2
    form2[18] = 0x20

    assert sector_layout(mode1, RAW_SECTOR_SIZE).data_offset == 16
    assert sector_layout(mode1, RAW_SECTOR_SIZE).data_size == 2048
    assert sector_layout(form2, RAW_SECTOR_SIZE).data_offset == 24
    assert sector_layout(form2, RAW_SECTOR_SIZE).data_size == 2324


def _mode2_form1_sector(data: bytes, sector_index: int) -> bytes:
    sector = bytearray(RAW_SECTOR_SIZE)
    sector[:12] = SYNC_HEADER
    sector[15] = 2
    sector[24:2072] = data
    return rebuild_psx_sector(bytes(sector), sector_index)
