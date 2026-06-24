from __future__ import annotations

from pathlib import Path
from shutil import copyfile

from src.core.binary_workbench.block_reader import CachedBinaryReader
from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.core.binary_workbench.psx_sector_layout import (
    binary_offset_for_internal,
    internal_file_spans,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_BINARY_OFFSET_COLUMN
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchRowDTO,
)


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


def build_internal_version_rows_from_overlay(
    source_path: Path,
    start_lba: int,
    internal_files: list[BinaryWorkbenchInternalFileDTO],
    sector_size: int,
    byte_overlays: dict[str, str],
    offset_names: list[str],
    offset_bases: dict[str, str],
    original_rows: list[BinaryWorkbenchRowDTO],
    current_rows: list[BinaryWorkbenchRowDTO],
) -> list[BinaryWorkbenchRowDTO]:
    target = next((item for item in internal_files if item.start_lba == start_lba), None)
    if target is None:
        return []
    spans = internal_file_spans(source_path, target, internal_files, sector_size)
    original_by_offset = {row.offsets.get("File"): row for row in original_rows}
    current_by_offset = {row.offsets.get("File"): row for row in current_rows}
    internal_size = spans[-1].internal_start + spans[-1].size if spans else 0
    rows: list[BinaryWorkbenchRowDTO] = []
    for row in build_version_rows_from_overlay(byte_overlays, offset_names, offset_bases):
        file_offset = row.offsets.get("File", "0x00000000")
        internal_offset = int(file_offset, 16)
        binary_offset = binary_offset_for_internal(spans, internal_offset)
        if binary_offset is None:
            continue
        original = original_by_offset.get(file_offset)
        current = current_by_offset.get(file_offset)
        modified = bytes.fromhex(row.bytes_text.replace(" ", ""))[: internal_size - internal_offset]
        if not modified:
            continue
        original_bytes = (
            bytes.fromhex(original.bytes_text.replace(" ", ""))[: len(modified)]
            if original is not None
            else b""
        )
        rows.append(BinaryWorkbenchRowDTO(
            offsets={**row.offsets, BINARY_WORKBENCH_BINARY_OFFSET_COLUMN: f"0x{binary_offset:08X}"},
            instruction=current.instruction if current is not None else "",
            bytes_text=" ".join(f"{byte:02X}" for byte in modified),
            original_instruction=original.instruction if original is not None else "",
            original_bytes_text=" ".join(f"{byte:02X}" for byte in original_bytes),
        ))
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
    if not _same_file(source_path, output_path):
        copyfile(source_path, output_path)
    with output_path.open("r+b") as target:
        for row in version_rows:
            offset = int(row.offsets.get("File", "0x0"), 16)
            target.seek(offset)
            target.write(bytes.fromhex(row.bytes_text.replace(" ", "")))


def _same_file(source_path: Path, output_path: Path) -> bool:
    try:
        return source_path.samefile(output_path)
    except OSError:
        return source_path.resolve() == output_path.resolve()


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
                target.write(codec.disassemble(chunk, offset + relative))
                target.write("\n")
            offset += max(1, block_size)


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
