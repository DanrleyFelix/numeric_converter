from __future__ import annotations

from pathlib import Path

from src.core.binary_workbench.block_reader import CachedBinaryReader
from src.core.binary_workbench.internal_file_reader import InternalFileView
from src.core.binary_workbench.internal_file_region import define_internal_file_region
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchTabContextDTO,
)


def reader_for_context(
    context: BinaryWorkbenchTabContextDTO,
    preferences: BinaryWorkbenchPreferencesDTO,
) -> CachedBinaryReader | InternalFileView | None:
    path = Path(context.source_path) if context.source_path else None
    if path is None or not path.exists():
        return None
    if context.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
        return CachedBinaryReader(path, preferences.block_size, preferences.cache_max_blocks)
    if context.kind != BINARY_WORKBENCH_TAB_KIND.INTERNAL:
        return None
    target = next(
        (
            item
            for item in context.internal_files
            if item.start_lba == context.internal_file_start_lba
        ),
        None,
    )
    if target is None:
        return None
    region = define_internal_file_region(
        path,
        target,
        context.internal_files,
        context.lba_sector_size,
    )
    return InternalFileView(region, preferences.block_size, preferences.cache_max_blocks)


def effective_reader_size(
    reader: CachedBinaryReader | InternalFileView,
    context_size: int,
) -> int:
    return max(reader.file_size, context_size)
