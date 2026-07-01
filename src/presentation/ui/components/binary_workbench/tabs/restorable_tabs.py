from pathlib import Path

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_VERSION_NAME,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
)
from src.presentation.repository.binary_workbench_workspace.constants import (
    VERSION_PATH_PREFIX,
    VERSIONS,
)


def restorable_state(state: BinaryWorkbenchStateDTO) -> BinaryWorkbenchStateDTO:
    tabs = [
        _with_default_version(tab)
        for tab in state.tabs
        if tab.kind == BINARY_WORKBENCH_TAB_KIND.SCRATCH or source_exists(tab)
    ]
    active = state.active_tab_id if any(tab.tab_id == state.active_tab_id for tab in tabs) else None
    return BinaryWorkbenchStateDTO(
        tabs=tabs,
        active_tab_id=active or (tabs[0].tab_id if tabs else None),
        share_view_preferences=state.share_view_preferences,
        directories=dict(state.directories),
        commands_by_arch={
            arch: {name: list(lines) for name, lines in commands.items()}
            for arch, commands in state.commands_by_arch.items()
        },
        encoding_tables=list(state.encoding_tables),
        window_size=state.window_size,
    )


def source_exists(tab: BinaryWorkbenchTabContextDTO) -> bool:
    return bool(tab.source_path) and Path(tab.source_path).exists()


def _with_default_version(tab: BinaryWorkbenchTabContextDTO) -> BinaryWorkbenchTabContextDTO:
    if tab.kind not in {
        BINARY_WORKBENCH_TAB_KIND.BINARY,
        BINARY_WORKBENCH_TAB_KIND.INTERNAL,
        BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
    }:
        return tab
    if tab.versions:
        active = tab.active_version_name or tab.versions[0].name
        return BinaryWorkbenchTabContextDTO(**{**tab.__dict__, "active_version_name": active})
    if tab.active_version_name and _has_version_module(tab):
        return tab
    version = BinaryWorkbenchVersionDTO(name=BINARY_WORKBENCH_DEFAULT_VERSION_NAME)
    return BinaryWorkbenchTabContextDTO(
        **{
            **tab.__dict__,
            "versions": [version],
            "active_version_name": version.name,
        }
    )


def _has_version_module(tab: BinaryWorkbenchTabContextDTO) -> bool:
    return VERSIONS in tab.module_paths or any(
        key.startswith(VERSION_PATH_PREFIX)
        for key in tab.module_paths
    )
