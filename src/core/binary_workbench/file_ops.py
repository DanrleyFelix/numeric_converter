from __future__ import annotations

from pathlib import Path
from shutil import copyfile

from src.core.binary_workbench.block_reader import CachedBinaryReader
from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchRowDTO,
)

_RAM_BASE = 0x80010000
_SECTOR_SIZE = 2352
_SECTOR_DATA_OFFSET = 24
_SECTOR_DATA_SIZE = 2048


def build_modified_rows(
    current_rows: list[BinaryWorkbenchRowDTO], original_rows: list[BinaryWorkbenchRowDTO]
) -> list[BinaryWorkbenchRowDTO]:
    original_by_offset = {row.offsets.get("File"): row for row in original_rows}
    return [
        row
        for row in current_rows
        if row.offsets.get("File") in original_by_offset
        and row.bytes_text != original_by_offset[row.offsets.get("File")].bytes_text
    ]


def apply_version_rows(
    original_rows: list[BinaryWorkbenchRowDTO], version_rows: list[BinaryWorkbenchRowDTO]
) -> list[BinaryWorkbenchRowDTO]:
    version_by_offset = {row.offsets.get("File"): row for row in version_rows}
    return [
        version_by_offset.get(row.offsets.get("File"), row)
        for row in original_rows
    ]


def build_version_rows_from_overlay(
    byte_overlays: dict[str, str],
    offset_names: list[str],
    offset_bases: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    rows: list[BinaryWorkbenchRowDTO] = []
    for key, bytes_text in sorted(byte_overlays.items()):
        offset = int(key, 16)
        rows.append(
            BinaryWorkbenchRowDTO(
                offsets=_offset_values(offset, offset_names, offset_bases),
                bytes_text=bytes_text,
            )
        )
    return rows


def overlay_from_version_rows(
    version_rows: list[BinaryWorkbenchRowDTO],
) -> dict[str, str]:
    return {
        row.offsets.get("File", "0x00000000"): row.bytes_text
        for row in version_rows
    }


def save_versioned_binary(
    source_path: Path, output_path: Path, version_rows: list[BinaryWorkbenchRowDTO]
) -> None:
    copyfile(source_path, output_path)
    with output_path.open("r+b") as target:
        for row in version_rows:
            offset = int(row.offsets.get("File", "0x0"), 16)
            target.seek(offset)
            target.write(bytes.fromhex(row.bytes_text.replace(" ", "")))


def save_binary_as_assembly(
    source_path: Path,
    output_path: Path,
    block_size: int,
    cache_max_blocks: int,
    byte_overlays: dict[str, str],
) -> None:
    codec = PsxMipsR3000ACodec()
    reader = CachedBinaryReader(source_path, block_size, cache_max_blocks)
    overlays = _overlay_bytes(byte_overlays)
    with _assembly_path(output_path).open("w", encoding="utf-8") as target:
        offset = 0
        while offset < reader.file_size:
            data = reader.read(offset, block_size, overlays)
            for relative in range(0, len(data), 4):
                chunk = data[relative : relative + 4].ljust(4, b"\x00")
                target.write(codec.disassemble(chunk, _RAM_BASE + offset + relative))
                target.write("\n")
            offset += max(1, block_size)


def extract_internal_file_bytes(
    source_path: Path,
    target: BinaryWorkbenchInternalFileDTO,
    internal_files: list[BinaryWorkbenchInternalFileDTO],
    sector_size: int = _SECTOR_SIZE,
) -> bytes:
    source = source_path.read_bytes()
    sorted_files = sorted(internal_files, key=lambda item: item.start_lba)
    next_file = next(
        (item for item in sorted_files if item.start_lba > target.start_lba),
        None,
    )
    start = target.start_lba * sector_size
    end = (next_file.start_lba * sector_size) if next_file else len(source)
    sectors = source[start:end]
    if sector_size != _SECTOR_SIZE:
        return sectors
    payload = bytearray()
    for index in range(0, len(sectors), sector_size):
        sector = sectors[index : index + sector_size]
        payload.extend(sector[_SECTOR_DATA_OFFSET : _SECTOR_DATA_OFFSET + _SECTOR_DATA_SIZE])
    return bytes(payload)


def _assembly_path(path: Path) -> Path:
    return path if path.suffix.lower() == ".asm" else path.with_suffix(".asm")


def _overlay_bytes(values: dict[str, str]) -> dict[int, bytes]:
    return {
        int(offset, 16): bytes.fromhex(bytes_text.replace(" ", ""))
        for offset, bytes_text in values.items()
    }


def _offset_values(
    offset: int,
    offset_names: list[str],
    offset_bases: dict[str, str],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in offset_names:
        base = 0 if name == "File" else int(offset_bases.get(name, "0x0"), 0)
        values[name] = f"0x{base + offset:08X}"
    return values
