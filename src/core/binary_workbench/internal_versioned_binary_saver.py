from __future__ import annotations

from pathlib import Path
from shutil import copyfile

from src.core.binary_workbench.internal_file_patch import InternalFilePatch
from src.core.binary_workbench.internal_file_region import InternalFileRegion
from src.core.binary_workbench.internal_offset_mapper import InternalOffsetMapper
from src.core.binary_workbench.psx_sector_io import RAW_SECTOR_SIZE, rebuild_psx_sector


def save_internal_versioned_binary(
    region: InternalFileRegion,
    output_path: Path,
    patches: list[InternalFilePatch],
) -> None:
    if not _same_file(region.source_path, output_path):
        copyfile(region.source_path, output_path)
    mapper = InternalOffsetMapper(region)
    affected: set[int] = set()
    with output_path.open("r+b") as target:
        for patch in patches:
            for chunk in mapper.chunks_for_internal_range(
                patch.internal_offset,
                len(patch.modified_bytes),
            ):
                patch_start = chunk.internal_offset - patch.internal_offset
                target.seek(chunk.binary_offset)
                target.write(patch.modified_bytes[patch_start : patch_start + chunk.size])
                affected.add(chunk.sector_index)
        if region.sector_size == RAW_SECTOR_SIZE:
            for sector_index in sorted(affected):
                _rebuild_sector_at(target, sector_index)


def _rebuild_sector_at(target, sector_index: int) -> None:
    offset = sector_index * RAW_SECTOR_SIZE
    target.seek(offset)
    sector = target.read(RAW_SECTOR_SIZE)
    rebuilt = rebuild_psx_sector(sector, sector_index)
    if rebuilt != sector:
        target.seek(offset)
        target.write(rebuilt)


def _same_file(source_path: Path, output_path: Path) -> bool:
    try:
        return source_path.samefile(output_path)
    except OSError:
        return source_path.resolve() == output_path.resolve()
