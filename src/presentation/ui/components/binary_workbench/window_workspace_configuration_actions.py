from pathlib import Path

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.presentation.repository.binary_workbench_workspace.constants import ENCODING_TABLES, OFFSET_REGIONS
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.environment import (
    BinaryWorkbenchEncodingTablesDialog,
    BinaryWorkbenchOffsetRegionsDialog,
)
from src.presentation.ui.components.binary_workbench.preferences import BinaryWorkbenchViewDialog


class BinaryWorkbenchWindowWorkspaceConfigurationMixin:
    def _open_view(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchViewDialog(
            current.reference_offsets,
            current.view_preferences.visible_columns,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.tabs.set_current_visible_columns(dialog.visible_columns())
        self.tabs.save_current_workspace()

    def _open_encoding_tables(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        directory = (
            self.tabs.directory_for(BINARY_WORKBENCH_STATE.ENCODING_TABLES_DIRECTORY)
            or self.tabs.decoded_tables_directory()
        )
        dialog = BinaryWorkbenchEncodingTablesDialog(
            current.encoding_tables,
            current.view_preferences.decoded_text_tables,
            directory,
            self,
        )
        dialog.exec()
        for path in dialog.loaded_paths():
            self.tabs.import_environment_file(ENCODING_TABLES, path)
        self.tabs.set_current_encoding_tables(dialog.tables(), dialog.enabled_names())

    def _open_offset_regions(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        if _scratch_workspace_source_required(current):
            self._show_warning_status(BINARY_WORKBENCH_TEXT.STATUS_WORKSPACE_SOURCE_REQUIRED)
            return
        dialog = BinaryWorkbenchOffsetRegionsDialog(
            self.tabs.offset_regions_for_current_context(),
            self.tabs.directory_for(BINARY_WORKBENCH_STATE.OFFSET_REGIONS_DIRECTORY),
            self,
            details_loader=self.tabs.offset_region_details_for_current_context,
            details_source_path=Path(current.module_paths[OFFSET_REGIONS])
            if current.module_paths.get(OFFSET_REGIONS)
            else None,
        )
        dialog.directoryChanged.connect(
            lambda value: self.tabs.set_directory(
                BINARY_WORKBENCH_STATE.OFFSET_REGIONS_DIRECTORY,
                Path(value),
            )
        )
        dialog.goToRequested.connect(self.tabs.go_to_offset)
        dialog.exec()
        self.tabs.set_current_offset_regions(dialog.mappings())
        module_path = dialog.saved_path() or dialog.loaded_path()
        if module_path:
            self.tabs.set_current_module_path(OFFSET_REGIONS, Path(module_path))
        self.tabs.save_current_workspace()


def _scratch_workspace_source_required(current) -> bool:
    return (
        current is not None
        and current.kind == BINARY_WORKBENCH_TAB_KIND.SCRATCH
        and not current.source_path
    )
