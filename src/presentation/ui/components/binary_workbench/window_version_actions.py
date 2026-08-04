from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.presentation.ui.components.binary_workbench.constants import (
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


VERSION_UPDATE_POPUP_SUPPRESSION_MS = 120


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
        current = self.tabs.current_context()
        if _scratch_workspace_source_required(current):
            self._show_warning_status(BINARY_WORKBENCH_TEXT.STATUS_WORKSPACE_SOURCE_REQUIRED)
            return
        dialog = BinaryWorkbenchVersionNameDialog(BINARY_WORKBENCH_TEXT.CREATE_VERSION, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.version_name():
            return
        if self.tabs.create_version(dialog.version_name()):
            self.tabs.save_current_workspace()
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_CREATED_TEMPLATE.format(name=dialog.version_name()), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self._show_unsupported_version_status(current)

    def _update_version(self) -> None:
        self._set_editor_popups_suppressed(True)
        try:
            barrier = self.tabs.ensure_current_consistent("save-version")
            if not barrier.success:
                self._show_status(barrier.error or "Unable to update the current version.", 0, True)
                return
            current = self.tabs.current_context()
            if _scratch_workspace_source_required(current):
                self._show_warning_status(BINARY_WORKBENCH_TEXT.STATUS_WORKSPACE_SOURCE_REQUIRED)
                return
            name = current.active_version_name if current is not None else ""
            if name:
                previous = current
                try:
                    updated = self.tabs.update_current_version(
                        name,
                        mark_dirty=False,
                        reload_page=False,
                        ensure_consistency=False,
                    )
                    saved = updated and self.tabs.save_current_workspace()
                except (OSError, TypeError, ValueError) as error:
                    saved = False
                    failure = str(error)
                else:
                    failure = "Unable to persist the current version atomically."
                if saved:
                    self.tabs.mark_initial_version_saved(current.tab_id)
                    self.tabs.backup_default_version_if_due()
                    self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_UPDATED_TEMPLATE.format(name=name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
                    return
                if previous is not None:
                    self.tabs._set_current_context_without_page_reload(previous)
                self._show_status(failure, 0, True)
                return
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
        finally:
            self._hide_editor_popups()
            QTimer.singleShot(
                VERSION_UPDATE_POPUP_SUPPRESSION_MS,
                lambda: self._set_editor_popups_suppressed(False),
            )

    def _set_editor_popups_suppressed(self, enabled: bool) -> None:
        grid = self._current_grid()
        if grid is not None:
            grid.set_editor_popups_suppressed(enabled)

    def _hide_editor_popups(self) -> None:
        grid = self._current_grid()
        if grid is not None:
            grid.hide_editor_popups()

    def _current_grid(self):
        page = self.tabs.currentWidget()
        return getattr(page, "grid", None)

    def _change_version(self) -> None:
        current = self.tabs.current_context()
        if not self._supports_versions(current):
            self._show_unsupported_version_status(current)
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
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_LOADED_TEMPLATE.format(name=name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)

    def _load_version(self) -> None:
        current = self.tabs.current_context()
        if not self._supports_versions(current):
            self._show_unsupported_version_status(current)
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

    @staticmethod
    def _supports_versions(current) -> bool:
        return current is not None and (
            current.kind in {
                BINARY_WORKBENCH_TAB_KIND.BINARY,
                BINARY_WORKBENCH_TAB_KIND.INTERNAL,
            }
            or current.kind == BINARY_WORKBENCH_TAB_KIND.ASSEMBLY
            and bool(current.source_path)
            and Path(current.source_path).is_file()
        )

    def _show_unsupported_version_status(self, current) -> None:
        if _scratch_workspace_source_required(current):
            self._show_warning_status(BINARY_WORKBENCH_TEXT.STATUS_WORKSPACE_SOURCE_REQUIRED)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_BINARY_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)


def _scratch_workspace_source_required(current) -> bool:
    return (
        current is not None
        and current.kind == BINARY_WORKBENCH_TAB_KIND.SCRATCH
        and not current.source_path
    )
