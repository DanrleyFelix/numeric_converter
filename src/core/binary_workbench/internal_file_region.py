from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO


@dataclass(frozen=True)
class InternalFileRegion:
    source_path: Path
    start_lba: int
    end_lba: int
    sector_size: int

    @property
    def sector_count(self) -> int:
        return max(0, self.end_lba - self.start_lba)

    @property
    def approximate_size(self) -> int:
        useful_size = 2048 if self.sector_size == 2352 else self.sector_size
        return self.sector_count * max(0, useful_size)


def define_internal_file_region(
    source_path: Path,
    target: BinaryWorkbenchInternalFileDTO,
    internal_files: list[BinaryWorkbenchInternalFileDTO],
    sector_size: int,
) -> InternalFileRegion:
    size = max(1, sector_size)
    source_size = source_path.stat().st_size if source_path.exists() else 0
    available_sectors = (source_size + size - 1) // size
    next_lba = next(
        (
            item.start_lba
            for item in sorted(internal_files, key=lambda item: item.start_lba)
            if item.start_lba > target.start_lba
        ),
        available_sectors,
    )
    start_lba = min(max(0, target.start_lba), available_sectors)
    end_lba = min(max(start_lba, next_lba), available_sectors)
    return InternalFileRegion(source_path, start_lba, end_lba, size)
