from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchViewPreferencesDTO,
)
from src.core.binary_workbench.mips_r3000a import (
    build_rows_from_bytes,
    build_rows_from_instructions,
    build_scratch_rows,
    extract_labels_from_instructions,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TAB_KIND,
)

_DEFAULT_REFS = ["File"]
_DEFAULT_REF_BASES = {"File": "0x00000000"}
_ASSEMBLY_SUFFIXES = {".asm", ".s"}


def create_binary_tab(state: BinaryWorkbenchStateDTO, path: Path) -> BinaryWorkbenchTabContextDTO:
    read_mode = _resolve_read_mode(path, "auto")
    block_size = BINARY_WORKBENCH_LAYOUT.DEFAULT_BLOCK_SIZE
    rows = _rows_from_path(path, read_mode, list(_DEFAULT_REFS), block_size, dict(_DEFAULT_REF_BASES))
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.BINARY,
        display_name=path.name,
        source_path=str(path),
        read_mode=read_mode,
        reference_offsets=list(_DEFAULT_REFS),
        reference_offset_bases=dict(_DEFAULT_REF_BASES),
        original_rows=deepcopy(rows),
        rows=rows,
        file_size=path.stat().st_size if path.exists() else 0,
        block_size=block_size,
        view_preferences=_seed_view_preferences(state),
    )


def create_file_tab(state: BinaryWorkbenchStateDTO, path: Path) -> BinaryWorkbenchTabContextDTO:
    if is_assembly_path(path):
        return create_assembly_tab(state, path)
    return create_binary_tab(state, path)


def create_assembly_tab(state: BinaryWorkbenchStateDTO, path: Path) -> BinaryWorkbenchTabContextDTO:
    read_mode = _resolve_read_mode(path, "assembly")
    rows = _rows_from_path(
        path,
        read_mode,
        list(_DEFAULT_REFS),
        BINARY_WORKBENCH_LAYOUT.DEFAULT_BLOCK_SIZE,
        dict(_DEFAULT_REF_BASES),
    )
    labels = _labels_from_path(path, read_mode)
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
        display_name=path.name,
        source_path=str(path),
        read_mode=read_mode,
        reference_offsets=list(_DEFAULT_REFS),
        reference_offset_bases=dict(_DEFAULT_REF_BASES),
        labels=labels,
        symbol_offsets={name: [offset] for name, offset in labels.items()},
        original_rows=deepcopy(rows),
        rows=rows,
        view_preferences=_seed_view_preferences(state),
    )


def create_scratch_tab(state: BinaryWorkbenchStateDTO) -> BinaryWorkbenchTabContextDTO:
    rows = build_scratch_rows(list(_DEFAULT_REFS), dict(_DEFAULT_REF_BASES))
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.SCRATCH,
        display_name=_next_display_name(state, "scratch.asm"),
        read_mode="assembly",
        reference_offsets=list(_DEFAULT_REFS),
        reference_offset_bases=dict(_DEFAULT_REF_BASES),
        original_rows=deepcopy(rows),
        rows=rows,
        view_preferences=_seed_view_preferences(state),
    )


def create_internal_tab(
    state: BinaryWorkbenchStateDTO,
    parent: BinaryWorkbenchTabContextDTO,
    internal_file: BinaryWorkbenchInternalFileDTO,
    data: bytes,
) -> BinaryWorkbenchTabContextDTO:
    rows = build_rows_from_bytes(
        data,
        list(parent.reference_offsets),
        0,
        dict(parent.reference_offset_bases),
    )
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.INTERNAL,
        display_name=internal_file.name,
        source_path=parent.source_path,
        cpu_arch=parent.cpu_arch,
        read_mode="bytes",
        navigation_mode=parent.navigation_mode,
        reference_offsets=list(parent.reference_offsets),
        reference_offset_bases=dict(parent.reference_offset_bases),
        labels=dict(parent.labels),
        equates=dict(parent.equates),
        variables=dict(parent.variables),
        internal_files=list(parent.internal_files),
        named_regions=list(parent.named_regions),
        versions=list(parent.versions),
        active_version_name=parent.active_version_name,
        last_open_offset=parent.last_open_offset,
        navigation_history=list(parent.navigation_history),
        original_rows=deepcopy(rows),
        rows=rows,
        view_preferences=_seed_view_preferences(state, parent.view_preferences),
    )


def restorable_state(state: BinaryWorkbenchStateDTO) -> BinaryWorkbenchStateDTO:
    tabs = [tab for tab in state.tabs if tab.kind == BINARY_WORKBENCH_TAB_KIND.SCRATCH or _source_exists(tab)]
    active = state.active_tab_id if any(tab.tab_id == state.active_tab_id for tab in tabs) else None
    return BinaryWorkbenchStateDTO(
        tabs=tabs,
        active_tab_id=active or (tabs[0].tab_id if tabs else None),
        share_view_preferences=state.share_view_preferences,
        recent_files=list(state.recent_files),
        directories=dict(state.directories),
    )


def _seed_view_preferences(
    state: BinaryWorkbenchStateDTO,
    preferred: BinaryWorkbenchViewPreferencesDTO | None = None,
) -> BinaryWorkbenchViewPreferencesDTO:
    if preferred is not None:
        return _copy_view_preferences(preferred)
    if not state.share_view_preferences or not state.tabs:
        return BinaryWorkbenchViewPreferencesDTO()
    active = next((tab for tab in state.tabs if tab.tab_id == state.active_tab_id), None)
    return _copy_view_preferences(active.view_preferences) if active else BinaryWorkbenchViewPreferencesDTO()


def _next_display_name(state: BinaryWorkbenchStateDTO, filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    count = sum(1 for tab in state.tabs if Path(tab.display_name).stem.startswith(stem))
    return f"{stem}_{count + 1}{suffix}"


def _source_exists(tab: BinaryWorkbenchTabContextDTO) -> bool:
    return bool(tab.source_path) and Path(tab.source_path).exists()


def _copy_view_preferences(
    value: BinaryWorkbenchViewPreferencesDTO,
) -> BinaryWorkbenchViewPreferencesDTO:
    return BinaryWorkbenchViewPreferencesDTO(
        visible_columns=deepcopy(value.visible_columns),
        decoded_text_tables=list(value.decoded_text_tables),
        group_bytes=value.group_bytes,
    )


def reload_source_rows(
    path: Path,
    read_mode: str,
    offsets: list[str],
    block_size: int,
    offset_bases: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    return _rows_from_path(path, _resolve_read_mode(path, read_mode), offsets, block_size, offset_bases)


def is_assembly_path(path: Path) -> bool:
    return path.suffix.lower() in _ASSEMBLY_SUFFIXES


def load_more_binary_rows(
    path: Path,
    offsets: list[str],
    start_offset: int,
    block_size: int,
    offset_bases: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    if not path.exists():
        return []
    with path.open("rb") as source:
        source.seek(start_offset)
        data = source.read(block_size)
    return build_rows_from_bytes(data, offsets, start_offset, offset_bases)


def _rows_from_path(
    path: Path,
    read_mode: str,
    offsets: list[str],
    block_size: int,
    offset_bases: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    if _resolve_read_mode(path, read_mode) == "assembly":
        lines = (
            path.read_text(encoding="utf-8", errors="replace").splitlines()
            if path.exists()
            else []
        )
        return build_rows_from_instructions(lines, offsets, offset_bases)
    return load_more_binary_rows(path, offsets, 0, block_size, offset_bases)


def _resolve_read_mode(path: Path, requested: str) -> str:
    if requested == "auto":
        return "assembly" if is_assembly_path(path) else "bytes"
    return requested


def _labels_from_path(path: Path, read_mode: str) -> dict[str, str]:
    if _resolve_read_mode(path, read_mode) != "assembly" or not path.exists():
        return {}
    return extract_labels_from_instructions(
        path.read_text(encoding="utf-8", errors="replace").splitlines()
    )
