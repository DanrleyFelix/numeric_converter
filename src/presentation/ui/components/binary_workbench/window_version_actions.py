from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.file_dialogs import (
    BinaryWorkbenchVersionActionsDialog,
    BinaryWorkbenchVersionChangeDialog,
    BinaryWorkbenchVersionNameDialog,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class BinaryWorkbenchWindowVersionMixin:
    def _open_version_actions(self) -> None:
        dialog = BinaryWorkbenchVersionActionsDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        action = dialog.selected_action()
        if action == BinaryWorkbenchVersionActionsDialog.LOAD:
            self._load_version()
        if action == BinaryWorkbenchVersionActionsDialog.CHANGE:
            self._change_version()
        if action == BinaryWorkbenchVersionActionsDialog.UPDATE:
            self._update_version()
        if action == BinaryWorkbenchVersionActionsDialog.CREATE:
            self._create_version()

    def _create_version(self) -> None:
        dialog = BinaryWorkbenchVersionNameDialog(BINARY_WORKBENCH_TEXT.CREATE_VERSION, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.version_name():
            return
        if self.tabs.create_version(dialog.version_name()):
            self.tabs.save_current_workspace()
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_CREATED_TEMPLATE.format(name=dialog.version_name()), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_BINARY_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)

    def _update_version(self) -> None:
        current = self.tabs.current_context()
        name = current.active_version_name if current is not None else ""
        if name and self.tabs.update_current_version(name):
            self.tabs.save_current_workspace()
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_UPDATED_TEMPLATE.format(name=name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)

    def _change_version(self) -> None:
        current = self.tabs.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_BINARY_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        if not current.versions:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        dialog = BinaryWorkbenchVersionChangeDialog(
            current.versions,
            current.active_version_name,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        name = dialog.selected_name()
        if name is not None and self.tabs.load_version(name):
            self.tabs.save_current_workspace()
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_LOADED_TEMPLATE.format(name=name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)

    def _load_version(self) -> None:
        current = self.tabs.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_BINARY_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_LOAD_TITLE,
            self.tabs.directory_for(BINARY_WORKBENCH_STATE.VERSIONS_DIRECTORY),
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_JSON_FILTER,
        )
        if not path:
            return
        name = self.tabs.load_versions_file(Path(path))
        if name is not None:
            self.tabs.save_current_workspace()
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_LOADED_TEMPLATE.format(name=name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
