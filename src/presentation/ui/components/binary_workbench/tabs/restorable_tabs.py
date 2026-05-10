from pathlib import Path

from src.modules.dtos import BinaryWorkbenchStateDTO, BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TAB_KIND


def restorable_state(state: BinaryWorkbenchStateDTO) -> BinaryWorkbenchStateDTO:
    tabs = [
        tab
        for tab in state.tabs
        if tab.kind == BINARY_WORKBENCH_TAB_KIND.SCRATCH or source_exists(tab)
    ]
    active = state.active_tab_id if any(tab.tab_id == state.active_tab_id for tab in tabs) else None
    return BinaryWorkbenchStateDTO(
        tabs=tabs,
        active_tab_id=active or (tabs[0].tab_id if tabs else None),
        share_view_preferences=state.share_view_preferences,
        recent_files=list(state.recent_files),
        directories=dict(state.directories),
        lba_filesystems=list(state.lba_filesystems),
        symbols=list(state.symbols),
    )


def source_exists(tab: BinaryWorkbenchTabContextDTO) -> bool:
    return bool(tab.source_path) and Path(tab.source_path).exists()
