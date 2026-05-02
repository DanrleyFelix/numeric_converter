from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from src.modules.dtos import (
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchViewPreferencesDTO,
)
from src.core.binary_workbench.mips_r3000a import (
    build_rows_from_bytes,
    build_rows_from_instructions,
    build_scratch_rows,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TAB_KIND

_DEFAULT_REFS = ["File", "RAM", "SLUS"]


def create_binary_tab(state: BinaryWorkbenchStateDTO, path: Path) -> BinaryWorkbenchTabContextDTO:
    data = path.read_bytes() if path.exists() else b""
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.BINARY,
        display_name=path.name,
        source_path=str(path),
        reference_offsets=list(_DEFAULT_REFS),
        rows=build_rows_from_bytes(data[:128], list(_DEFAULT_REFS)),
        view_preferences=_seed_view_preferences(state),
    )


def create_assembly_tab(state: BinaryWorkbenchStateDTO, path: Path) -> BinaryWorkbenchTabContextDTO:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
        display_name=path.name,
        source_path=str(path),
        reference_offsets=list(_DEFAULT_REFS),
        rows=build_rows_from_instructions(lines[:32], list(_DEFAULT_REFS)),
        view_preferences=_seed_view_preferences(state),
    )


def create_scratch_tab(state: BinaryWorkbenchStateDTO) -> BinaryWorkbenchTabContextDTO:
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.SCRATCH,
        display_name=_next_display_name(state, "scratch.asm"),
        reference_offsets=list(_DEFAULT_REFS),
        rows=build_scratch_rows(list(_DEFAULT_REFS)),
        view_preferences=_seed_view_preferences(state),
    )


def create_internal_tab(
    state: BinaryWorkbenchStateDTO,
    parent: BinaryWorkbenchTabContextDTO,
) -> BinaryWorkbenchTabContextDTO:
    return BinaryWorkbenchTabContextDTO(
        tab_id=uuid4().hex,
        kind=BINARY_WORKBENCH_TAB_KIND.INTERNAL,
        display_name=_next_display_name(state, "internal.bin"),
        source_path=parent.source_path,
        cpu_arch=parent.cpu_arch,
        navigation_mode=parent.navigation_mode,
        reference_offsets=list(parent.reference_offsets),
        labels=dict(parent.labels),
        equates=dict(parent.equates),
        variables=dict(parent.variables),
        internal_files=list(parent.internal_files),
        named_regions=list(parent.named_regions),
        versions=list(parent.versions),
        last_open_offset=parent.last_open_offset,
        navigation_history=list(parent.navigation_history),
        rows=deepcopy(parent.rows[:16]),
        view_preferences=_seed_view_preferences(state, parent.view_preferences),
    )


def restorable_state(state: BinaryWorkbenchStateDTO) -> BinaryWorkbenchStateDTO:
    tabs = [tab for tab in state.tabs if tab.kind == BINARY_WORKBENCH_TAB_KIND.SCRATCH or _source_exists(tab)]
    active = state.active_tab_id if any(tab.tab_id == state.active_tab_id for tab in tabs) else None
    return BinaryWorkbenchStateDTO(
        tabs=tabs,
        active_tab_id=active or (tabs[0].tab_id if tabs else None),
        share_view_preferences=state.share_view_preferences,
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
    )
