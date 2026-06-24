from __future__ import annotations

from pathlib import Path

from src.core.binary_workbench.internal_file_patch import patches_from_overlays
from src.core.binary_workbench.internal_file_reader import InternalFileView
from src.core.binary_workbench.internal_file_region import define_internal_file_region
from src.core.binary_workbench.version_overlays import offset_values
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_BINARY_OFFSET_COLUMN,
    BINARY_WORKBENCH_DEFAULT_BLOCK_SIZE,
    BINARY_WORKBENCH_DEFAULT_CACHE_MAX_BLOCKS,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO, BinaryWorkbenchRowDTO


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
    region = define_internal_file_region(source_path, target, internal_files, sector_size)
    view = InternalFileView(
        region,
        BINARY_WORKBENCH_DEFAULT_BLOCK_SIZE,
        BINARY_WORKBENCH_DEFAULT_CACHE_MAX_BLOCKS,
    )
    original_by_offset = {row.offsets.get("File"): row for row in original_rows}
    current_by_offset = {row.offsets.get("File"): row for row in current_rows}
    rows: list[BinaryWorkbenchRowDTO] = []
    for patch in patches_from_overlays(view, byte_overlays):
        file_offset = f"0x{patch.internal_offset:08X}"
        binary_offset = view.binary_offset_for_internal(patch.internal_offset)
        original = original_by_offset.get(file_offset)
        current = current_by_offset.get(file_offset)
        offsets = offset_values(patch.internal_offset, offset_names, offset_bases)
        if binary_offset is not None:
            offsets[BINARY_WORKBENCH_BINARY_OFFSET_COLUMN] = f"0x{binary_offset:08X}"
        rows.append(BinaryWorkbenchRowDTO(
            offsets=offsets,
            instruction=current.instruction if current is not None else "",
            bytes_text=" ".join(f"{byte:02X}" for byte in patch.modified_bytes),
            original_instruction=original.instruction if original is not None else "",
            original_bytes_text=" ".join(f"{byte:02X}" for byte in patch.original_bytes),
        ))
    return rows
