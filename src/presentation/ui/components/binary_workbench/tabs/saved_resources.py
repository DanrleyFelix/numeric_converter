from pathlib import Path

from src.core.binary_workbench.resource_identity import matching_file_identifiers
from src.modules.binary_workbench_dtos import BinaryWorkbenchLbaFilesystemDTO, BinaryWorkbenchStateDTO, BinaryWorkbenchSymbolsDTO


def matching_lba_filesystem(
    state: BinaryWorkbenchStateDTO,
    path: Path,
) -> BinaryWorkbenchLbaFilesystemDTO | None:
    return next(
        (
            item
            for item in state.lba_filesystems
            if matching_file_identifiers(item.file_identifiers, path)
        ),
        None,
    )


def matching_symbols(
    state: BinaryWorkbenchStateDTO,
    path: Path,
) -> BinaryWorkbenchSymbolsDTO | None:
    return next(
        (
            item
            for item in state.symbols
            if matching_file_identifiers(item.file_identifiers, path)
        ),
        None,
    )
