from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.native_dialogs import (
    ask_close_tab_with_native_system_dialog,
)
from src.presentation.ui.components.binary_workbench.file_dialogs import (
    BinaryWorkbenchVersionNameDialog,
)


class BinaryWorkbenchWindowCloseMixin:
    def _request_tab_close(self, index: int) -> None:
        close_indices = self._tab_close_indices(index)
        if not close_indices:
            return
        original_index = self.tabs.currentIndex()
        suspended_pages = []
        for close_index in close_indices:
            self.tabs.setCurrentIndex(close_index)
            page = self.tabs.widget(close_index)
            if hasattr(page, "suspend_eventual_consistency"):
                suspended_pages.append(
                    (page, page.suspend_eventual_consistency())
                )
            # Do not run the global Assembly barrier before the native prompt.
            # Unsaved detection flushes only the coalesced local edit; the
            # expensive barrier remains exclusive to the user's Save choice.
            if not self.tabs.has_unsaved_changes(close_index):
                continue
            response = self._native_close_question()
            if response == QMessageBox.StandardButton.Cancel:
                _resume_suspended_pages(suspended_pages)
                if 0 <= original_index < self.tabs.count():
                    self.tabs.setCurrentIndex(original_index)
                return
            if response == QMessageBox.StandardButton.Discard:
                self.tabs.discard_internal_changes(close_index)
            if response == QMessageBox.StandardButton.Save and not self._save_current_tab_for_close():
                _resume_suspended_pages(suspended_pages)
                if 0 <= original_index < self.tabs.count():
                    self.tabs.setCurrentIndex(original_index)
                return
        for close_index in sorted(close_indices, reverse=True):
            self.tabs.close_tab(close_index)

    def _tab_close_indices(self, index: int) -> list[int]:
        target = self.tabs.context_at(index)
        if target is None:
            return []
        if target.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return [index]
        return [
            *[
                child_index
                for child_index in range(self.tabs.count())
                if child_index != index
                and _is_internal_child(self.tabs.context_at(child_index), target)
            ],
            index,
        ]

    def _native_close_question(self) -> QMessageBox.StandardButton:
        return ask_close_tab_with_native_system_dialog(self)

    def _save_current_tab_for_close(self) -> bool:
        # The native confirmation is intentionally shown before this barrier.
        # Once Save is chosen, however, persistence must consume one complete
        # Assembly revision rather than whichever eventual batch last finished.
        if not self.tabs.commit_current_editor_text():
            return False
        current = self.tabs.current_context()
        if current is None:
            return False
        if current.kind in {
            BINARY_WORKBENCH_TAB_KIND.BINARY,
            BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
            BINARY_WORKBENCH_TAB_KIND.INTERNAL,
        }:
            return self._save_binary_workspace_for_close(current)
        if self._save_assembly_code():
            self.tabs.save_current_workspace()
            return True
        return False

    def _save_binary_workspace_for_close(self, current) -> bool:
        if (
            current.kind == BINARY_WORKBENCH_TAB_KIND.ASSEMBLY
            and (not current.source_path or not Path(current.source_path).is_file())
        ):
            self._show_warning_status(BINARY_WORKBENCH_TEXT.STATUS_WORKSPACE_SOURCE_REQUIRED)
            return False
        if self.tabs.has_unsaved_version_edits(current) and not current.active_version_name:
            dialog = BinaryWorkbenchVersionNameDialog(
                BINARY_WORKBENCH_TEXT.CREATE_VERSION,
                parent=self,
            )
            if dialog.exec() != dialog.DialogCode.Accepted or not dialog.version_name():
                return False
            if not self.tabs.create_version(dialog.version_name()):
                return False
        elif current.active_version_name:
            self.tabs.update_current_version(current.active_version_name)
        return self.tabs.save_current_workspace()


def _is_internal_child(child, parent) -> bool:
    return (
        child is not None
        and child.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL
        and (
            child.internal_parent_tab_id == parent.tab_id
            or bool(parent.source_path and child.source_path == parent.source_path)
        )
    )


def _resume_suspended_pages(suspended_pages) -> None:
    """Resume eventual work only for pages kept open by the close flow."""

    for page, suspended in suspended_pages:
        page.resume_eventual_consistency(suspended)
