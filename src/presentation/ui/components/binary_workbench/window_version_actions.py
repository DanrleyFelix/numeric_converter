from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.file_dialogs import (
    BinaryWorkbenchVersionNameDialog,
    BinaryWorkbenchVersionPickerDialog,
)


class BinaryWorkbenchWindowVersionMixin:
    def _create_version(self) -> None:
        dialog = BinaryWorkbenchVersionNameDialog(BINARY_WORKBENCH_TEXT.CREATE_VERSION, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.version_name():
            return
        if self.tabs.create_version(dialog.version_name()):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_CREATED_TEMPLATE.format(name=dialog.version_name()), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_BINARY_REQUIRED, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)

    def _update_version(self) -> None:
        current = self.tabs.current_context()
        initial_name = current.active_version_name if current is not None else ""
        dialog = BinaryWorkbenchVersionNameDialog(BINARY_WORKBENCH_TEXT.ATT_CURRENT_VERSION, initial_name, self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.version_name():
            return
        if self.tabs.update_current_version(dialog.version_name()):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_UPDATED_TEMPLATE.format(name=dialog.version_name()), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)

    def _load_version(self) -> None:
        current = self.tabs.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY or not current.versions:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        dialog = BinaryWorkbenchVersionPickerDialog(current.versions, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        name = dialog.selected_name()
        if name is not None and self.tabs.load_version(name):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_LOADED_TEMPLATE.format(name=name), BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
