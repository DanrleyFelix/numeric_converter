from pathlib import Path

from src.core.binary_workbench.internal_version_rows import build_internal_version_rows_from_overlay
from src.core.binary_workbench.internal_file_patch import (
    InternalFilePatch,
    binary_overlays_from_internal_overlays,
    internal_overlays_from_binary_overlays,
)
from src.core.binary_workbench.internal_file_reader import InternalFileView
from src.core.binary_workbench.internal_file_region import define_internal_file_region
from src.core.binary_workbench.internal_offset_mapper import InternalOffsetMapper
from src.core.binary_workbench.internal_versioned_binary_saver import save_internal_versioned_binary
from src.core.binary_workbench.psx_sector_io import rebuild_psx_sector
from src.core.binary_workbench.psx_sector_layout import RAW_SECTOR_SIZE, SYNC_HEADER, sector_layout
from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO, BinaryWorkbenchRowDTO


def test_internal_region_ends_at_next_lba_without_loading_payload(tmp_path: Path):
    source = tmp_path / "disc.bin"
    source.write_bytes(bytes(RAW_SECTOR_SIZE * 4))
    files = [BinaryWorkbenchInternalFileDTO("FIRST", 1), BinaryWorkbenchInternalFileDTO("NEXT", 3)]

    region = define_internal_file_region(source, files[0], files, RAW_SECTOR_SIZE)

    assert (region.start_lba, region.end_lba, region.sector_count) == (1, 3, 2)


def test_lazy_view_reads_only_useful_bytes_and_caches_requested_sector(tmp_path: Path):
    source = tmp_path / "disc.bin"
    payloads = [bytes([value]) * 2048 for value in (0x11, 0x22, 0x33)]
    source.write_bytes(b"".join(_mode2_form1_sector(data, index) for index, data in enumerate(payloads)))
    files = [BinaryWorkbenchInternalFileDTO("FILE", 0)]
    region = define_internal_file_region(source, files[0], files, RAW_SECTOR_SIZE)
    view = InternalFileView(region, block_size=2048, cache_max_blocks=2)

    assert view.read(2046, 6) == payloads[0][-2:] + payloads[1][:4]
    assert view.mapper.cached_sector_count == 2


def test_mapper_splits_range_at_useful_sector_boundary(tmp_path: Path):
    source = tmp_path / "disc.bin"
    source.write_bytes(_mode2_form1_sector(bytes(2048), 0) + _mode2_form1_sector(bytes(2048), 1))
    target = BinaryWorkbenchInternalFileDTO("FILE", 0)
    region = define_internal_file_region(source, target, [target], RAW_SECTOR_SIZE)

    chunks = InternalOffsetMapper(region).chunks_for_internal_range(2046, 4)

    assert [(chunk.binary_offset, chunk.size, chunk.sector_index) for chunk in chunks] == [
        (24 + 2046, 2, 0),
        (RAW_SECTOR_SIZE + 24, 2, 1),
    ]


def test_internal_and_binary_overlays_round_trip_across_sector_boundary(tmp_path: Path):
    source = tmp_path / "disc.bin"
    source.write_bytes(
        _mode2_form1_sector(bytes(2048), 0)
        + _mode2_form1_sector(bytes(2048), 1)
    )
    target = BinaryWorkbenchInternalFileDTO("FILE", 0)
    region = define_internal_file_region(source, target, [target], RAW_SECTOR_SIZE)
    mapper = InternalOffsetMapper(region)

    binary = binary_overlays_from_internal_overlays(
        mapper,
        {"0x000007FE": "AA BB CC DD"},
    )

    assert binary == {
        "0x00000816": "AA BB",
        "0x00000948": "CC DD",
    }
    assert internal_overlays_from_binary_overlays(mapper, binary) == {
        "0x000007FE": "AA BB CC DD",
    }


def test_mapper_adapts_when_sector_layout_changes(tmp_path: Path):
    source = tmp_path / "mixed.bin"
    source.write_bytes(
        _mode1_sector(bytes([0x11]) * 2048)
        + _mode2_form2_sector(bytes([0x22]) * 2324)
    )
    target = BinaryWorkbenchInternalFileDTO("FILE", 0)
    region = define_internal_file_region(source, target, [target], RAW_SECTOR_SIZE)
    view = InternalFileView(region, block_size=2048, cache_max_blocks=2)

    assert view.read(2046, 6) == bytes.fromhex("11 11 22 22 22 22")
    assert view.file_size == 2048 + 2324


def test_internal_version_rows_keep_internal_patch_and_original_bytes(tmp_path: Path):
    source = tmp_path / "disc.bin"
    source.write_bytes(_mode2_form1_sector(bytes(2048), 0))
    files = [BinaryWorkbenchInternalFileDTO("FILE", 0)]
    original = [BinaryWorkbenchRowDTO(offsets={"File": "0x00000000"}, instruction="nop", bytes_text="00 00 00 00")]
    current = [BinaryWorkbenchRowDTO(offsets={"File": "0x00000000"}, instruction="jr $ra", bytes_text="08 00 E0 03")]

    rows = build_internal_version_rows_from_overlay(
        source,
        0,
        files,
        RAW_SECTOR_SIZE,
        {"0x00000000": "08 00 E0 03"},
        ["File"],
        {"File": "0x00000000"},
        original,
        current,
    )

    assert rows[0].offsets == {"File": "0x00000000"}
    assert rows[0].original_bytes_text == "00 00 00 00"
    assert rows[0].bytes_text == "08 00 E0 03"


def test_save_splits_cross_sector_patch_and_rebuilds_only_affected_sectors(tmp_path: Path):
    source = tmp_path / "disc.bin"
    output = tmp_path / "patched.bin"
    sectors = [_mode2_form1_sector(bytes([value]) * 2048, index) for index, value in enumerate((0x11, 0x22, 0x33))]
    source.write_bytes(b"".join(sectors))
    target = BinaryWorkbenchInternalFileDTO("FILE", 0)
    region = define_internal_file_region(source, target, [target], RAW_SECTOR_SIZE)
    patch = InternalFilePatch(2046, bytes.fromhex("11 11 22 22"), bytes.fromhex("AA BB CC DD"))

    save_internal_versioned_binary(region, output, [patch])

    saved = output.read_bytes()
    assert saved[24 + 2046 : 24 + 2048] == bytes.fromhex("AA BB")
    assert saved[RAW_SECTOR_SIZE + 24 : RAW_SECTOR_SIZE + 26] == bytes.fromhex("CC DD")
    assert saved[RAW_SECTOR_SIZE * 2 :] == sectors[2]
    assert saved[:RAW_SECTOR_SIZE] == rebuild_psx_sector(saved[:RAW_SECTOR_SIZE], 0)
    assert saved[RAW_SECTOR_SIZE : RAW_SECTOR_SIZE * 2] == rebuild_psx_sector(
        saved[RAW_SECTOR_SIZE : RAW_SECTOR_SIZE * 2],
        1,
    )


def test_invalid_raw_sector_uses_safe_empty_layout():
    layout = sector_layout(bytes(24), RAW_SECTOR_SIZE, RAW_SECTOR_SIZE)

    assert layout.data_offset == 0
    assert layout.data_size == 0
    assert (layout.mode, layout.form) == (0, 0)


def _mode2_form1_sector(data: bytes, sector_index: int) -> bytes:
    sector = bytearray(RAW_SECTOR_SIZE)
    sector[:12] = SYNC_HEADER
    sector[15] = 2
    sector[24:2072] = data
    return rebuild_psx_sector(bytes(sector), sector_index)


def _mode1_sector(data: bytes) -> bytes:
    sector = bytearray(RAW_SECTOR_SIZE)
    sector[:12] = SYNC_HEADER
    sector[15] = 1
    sector[16:2064] = data
    return bytes(sector)


def _mode2_form2_sector(data: bytes) -> bytes:
    sector = bytearray(RAW_SECTOR_SIZE)
    sector[:12] = SYNC_HEADER
    sector[15] = 2
    sector[18] = 0x20
    sector[24:2348] = data
    return bytes(sector)
