from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from src.core.binary_workbench.mips_r3000a import build_scratch_rows
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE,
    BINARY_WORKBENCH_DEFAULT_VERSION_NAME,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets
from src.presentation.ui.components.binary_workbench.tabs.source_rows import (
    DEFAULT_REF_BASES,
    DEFAULT_REFS,
    is_assembly_path,
    labels_from_path,
    resolve_read_mode,
    rows_from_path,
)
from src.presentation.ui.components.binary_workbench.tabs.view_preferences import seed_view_preferences


def create_binary_tab(
    state: BinaryWorkbenchStateDTO,
    path: Path,
    preferences: BinaryWorkbenchPreferencesDTO | None = None,
) -> BinaryWorkbenchTabContextDTO:
    read_mode = resolve_read_mode(path, "auto")
    preferences = preferences or BinaryWorkbenchPreferencesDTO()
    block_size = preferences.block_size
    rows = rows_from_path(path, read_mode, list(DEFAULT_REFS), block_size, dict(DEFAULT_REF_BASES))
    variables: dict[str, str] = {}
    equates: dict[str, str] = {}
    labels: dict[str, str] = {}
    file_size = path.stat().st_size if path.exists() else 0
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
        internal_files=[],
        lba_sector_size=BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE,
        original_rows=deepcopy(rows),
        rows=rows,
        file_size=file_size,
        original_file_size=file_size,
        versions=[BinaryWorkbenchVersionDTO(name=BINARY_WORKBENCH_DEFAULT_VERSION_NAME)],
        active_version_name=BINARY_WORKBENCH_DEFAULT_VERSION_NAME,
        view_preferences=seed_view_preferences(state),
    )


def create_file_tab(
    state: BinaryWorkbenchStateDTO,
    path: Path,
    preferences: BinaryWorkbenchPreferencesDTO | None = None,
) -> BinaryWorkbenchTabContextDTO:
    return create_assembly_tab(state, path, preferences) if is_assembly_path(path) else create_binary_tab(state, path, preferences)


def create_assembly_tab(
    state: BinaryWorkbenchStateDTO,
    path: Path,
    preferences: BinaryWorkbenchPreferencesDTO | None = None,
) -> BinaryWorkbenchTabContextDTO:
    read_mode = resolve_read_mode(path, "assembly")
    preferences = preferences or BinaryWorkbenchPreferencesDTO()
    rows = rows_from_path(path, read_mode, list(DEFAULT_REFS), preferences.block_size, dict(DEFAULT_REF_BASES))
    variables: dict[str, str] = {}
    equates: dict[str, str] = {}
    labels = labels_from_path(path, read_mode)
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
        file_size=len(rows) * ROW_BYTES,
        original_file_size=len(rows) * ROW_BYTES,
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
        file_size=len(rows) * ROW_BYTES,
        original_file_size=len(rows) * ROW_BYTES,
        view_preferences=seed_view_preferences(state),
    )


def create_label_tab(parent: BinaryWorkbenchTabContextDTO, label: str) -> BinaryWorkbenchTabContextDTO:
    return BinaryWorkbenchTabContextDTO(
        **{
            **deepcopy(parent.__dict__),
            "tab_id": uuid4().hex,
            "display_name": BINARY_WORKBENCH_TEXT.LABEL_TAB_NAME_TEMPLATE.format(
                label=label,
                source=parent.display_name,
            ),
        }
    )


def next_display_name(state: BinaryWorkbenchStateDTO, filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    count = sum(1 for tab in state.tabs if Path(tab.display_name).stem.startswith(stem))
    return f"{stem}_{count + 1}{suffix}"
