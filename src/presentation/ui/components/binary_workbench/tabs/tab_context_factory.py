from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from src.core.binary_workbench.mips_r3000a import build_rows_from_bytes, build_scratch_rows
from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets
from src.presentation.ui.components.binary_workbench.tabs.saved_resources import (
    matching_lba_filesystem,
    matching_symbols,
)
from src.presentation.ui.components.binary_workbench.tabs.source_rows import (
    DEFAULT_REF_BASES,
    DEFAULT_REFS,
    is_assembly_path,
    labels_from_path,
    resolve_read_mode,
    rows_from_path,
)
from src.presentation.ui.components.binary_workbench.tabs.view_preferences import seed_view_preferences


def create_binary_tab(state: BinaryWorkbenchStateDTO, path: Path) -> BinaryWorkbenchTabContextDTO:
    read_mode = resolve_read_mode(path, "auto")
    block_size = BINARY_WORKBENCH_LAYOUT.DEFAULT_BLOCK_SIZE
    rows = rows_from_path(path, read_mode, list(DEFAULT_REFS), block_size, dict(DEFAULT_REF_BASES))
    lba_filesystem = matching_lba_filesystem(state, path)
    saved_symbols = matching_symbols(state, path)
    variables = dict(saved_symbols.variables) if saved_symbols else {}
    equates = dict(saved_symbols.equates) if saved_symbols else {}
    labels = dict(saved_symbols.labels) if saved_symbols else {}
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.BINARY,
        display_name=path.name,
        source_path=str(path),
        read_mode=read_mode,
        reference_offsets=list(DEFAULT_REFS),
        reference_offset_bases=dict(DEFAULT_REF_BASES),
        labels=labels,
        equates=equates,
        variables=variables,
        symbol_offsets=symbol_offsets(rows, variables, equates, labels),
        internal_files=list(lba_filesystem.internal_files) if lba_filesystem else [],
        lba_sector_size=lba_filesystem.sector_size if lba_filesystem else 2352,
        original_rows=deepcopy(rows),
        rows=rows,
        file_size=path.stat().st_size if path.exists() else 0,
        block_size=block_size,
        view_preferences=seed_view_preferences(state),
    )


def create_file_tab(state: BinaryWorkbenchStateDTO, path: Path) -> BinaryWorkbenchTabContextDTO:
    return create_assembly_tab(state, path) if is_assembly_path(path) else create_binary_tab(state, path)


def create_assembly_tab(state: BinaryWorkbenchStateDTO, path: Path) -> BinaryWorkbenchTabContextDTO:
    read_mode = resolve_read_mode(path, "assembly")
    rows = rows_from_path(path, read_mode, list(DEFAULT_REFS), BINARY_WORKBENCH_LAYOUT.DEFAULT_BLOCK_SIZE, dict(DEFAULT_REF_BASES))
    saved_symbols = matching_symbols(state, path)
    variables = dict(saved_symbols.variables) if saved_symbols else {}
    equates = dict(saved_symbols.equates) if saved_symbols else {}
    labels = {**labels_from_path(path, read_mode), **(dict(saved_symbols.labels) if saved_symbols else {})}
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
        display_name=path.name,
        source_path=str(path),
        read_mode=read_mode,
        reference_offsets=list(DEFAULT_REFS),
        reference_offset_bases=dict(DEFAULT_REF_BASES),
        labels=labels,
        equates=equates,
        variables=variables,
        symbol_offsets=symbol_offsets(rows, variables, equates, labels),
        original_rows=deepcopy(rows),
        rows=rows,
        view_preferences=seed_view_preferences(state),
    )


def create_scratch_tab(state: BinaryWorkbenchStateDTO) -> BinaryWorkbenchTabContextDTO:
    rows = build_scratch_rows(list(DEFAULT_REFS), dict(DEFAULT_REF_BASES))
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.SCRATCH,
        display_name=next_display_name(state, "scratch.asm"),
        read_mode="assembly",
        reference_offsets=list(DEFAULT_REFS),
        reference_offset_bases=dict(DEFAULT_REF_BASES),
        original_rows=deepcopy(rows),
        rows=rows,
        view_preferences=seed_view_preferences(state),
    )


def create_internal_tab(
    state: BinaryWorkbenchStateDTO,
    parent: BinaryWorkbenchTabContextDTO,
    internal_file: BinaryWorkbenchInternalFileDTO,
    data: bytes,
) -> BinaryWorkbenchTabContextDTO:
    rows = build_rows_from_bytes(data, list(parent.reference_offsets), 0, dict(parent.reference_offset_bases))
    return BinaryWorkbenchTabContextDTO(
        **{
            **parent.__dict__,
            "tab_id": uuid4().hex,
            "kind": BINARY_WORKBENCH_TAB_KIND.INTERNAL,
            "display_name": internal_file.name,
            "read_mode": "bytes",
            "original_rows": deepcopy(rows),
            "rows": rows,
            "view_preferences": seed_view_preferences(state, parent.view_preferences),
        }
    )


def next_display_name(state: BinaryWorkbenchStateDTO, filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    count = sum(1 for tab in state.tabs if Path(tab.display_name).stem.startswith(stem))
    return f"{stem}_{count + 1}{suffix}"
