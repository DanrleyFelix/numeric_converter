from pathlib import Path

from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.factory import restorable_state
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import state_payload, tab_text
from src.presentation.ui.components.binary_workbench.tabs.tab_workspace import DIRECTORY_KEYS


class TabStateMixin:
    def export_state(self) -> BinaryWorkbenchStateDTO:
        return self._state

    def load_state(self, state: BinaryWorkbenchStateDTO) -> None:
        self.clear()
        self._state = restorable_state(state)
        for tab in self._state.tabs:
            self._add_tab_page(tab)
        if self.count():
            self.setCurrentIndex(self._active_index())
        self.stateChanged.emit(self._state)

    def directory_for(self, action_key: str) -> str:
        if value := self._state.directories.get(action_key, ""):
            return value
        return self.workspace_module_directory(action_key)

    def set_directory(self, action_key: str, path: Path) -> None:
        module_key = DIRECTORY_KEYS.get(action_key)
        current = self.current_context()
        if module_key and current is not None:
            current = BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "module_directories": {
                        **current.module_directories,
                        module_key: str(path),
                    },
                }
            )
            self._replace_context(current.tab_id, current)
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "directories": {**self._state.directories, action_key: str(path)}}
        )
        self.stateChanged.emit(self._state)

    def current_context(self) -> BinaryWorkbenchTabContextDTO | None:
        index = self.currentIndex()
        return self._state.tabs[index] if 0 <= index < len(self._state.tabs) else None

    def context_at(self, index: int) -> BinaryWorkbenchTabContextDTO | None:
        return self._state.tabs[index] if 0 <= index < len(self._state.tabs) else None

    def has_unsaved_changes(self, index: int) -> bool:
        context = self.context_at(index)
        if context is None:
            return False
        if context.kind == "binary":
            return self.has_unsaved_version_edits(context) or self._has_workspace_module_changes(context)
        return self._controller.rows_have_unsaved_edits(
            context.rows,
            context.original_rows,
        ) or self._has_workspace_module_changes(context)

    def close_tab(self, index: int) -> None:
        if not 0 <= index < len(self._state.tabs):
            return
        closed = self._state.tabs[index]
        remaining = [tab for idx, tab in enumerate(self._state.tabs) if idx != index]
        self.removeTab(index)
        active = remaining[min(index, len(remaining) - 1)].tab_id if remaining else None
        self._state = BinaryWorkbenchStateDTO(**{**state_payload(self._state), "tabs": remaining, "active_tab_id": active})
        self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_CLOSED_TEMPLATE.format(name=closed.display_name))
        self.stateChanged.emit(self._state)

    def _append_tab(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "tabs": [*self._state.tabs, context], "active_tab_id": context.tab_id}
        )
        self._add_tab_page(context)
        self.setCurrentIndex(self.count() - 1)
        self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_OPENED_TEMPLATE.format(name=context.display_name))
        self.stateChanged.emit(self._state)

    def _replace_context(self, tab_id: str, context: object) -> None:
        if not isinstance(context, BinaryWorkbenchTabContextDTO):
            return
        tabs = [context if tab.tab_id == tab_id else tab for tab in self._state.tabs]
        self._state = BinaryWorkbenchStateDTO(**{**state_payload(self._state), "tabs": tabs})
        self._refresh_tab_label(tab_id, context.display_name)
        self.stateChanged.emit(self._state)

    def _set_current_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        index = self.currentIndex()
        if not 0 <= index < len(self._state.tabs):
            return
        self._replace_context(context.tab_id, context)
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.set_preferences(self._preferences)
            page.load_context(context)

    def _sync_active_tab(self, index: int) -> None:
        if not 0 <= index < len(self._state.tabs):
            return
        self._state = BinaryWorkbenchStateDTO(**{**state_payload(self._state), "active_tab_id": self._state.tabs[index].tab_id})
        self.stateChanged.emit(self._state)

    def _active_index(self) -> int:
        return next((idx for idx, tab in enumerate(self._state.tabs) if tab.tab_id == self._state.active_tab_id), 0)

    def _remember_file_path(self, action_key: str, path: Path) -> None:
        text_path = str(path)
        self._program_context = self._controller.remember_recent_file(
            self._program_context,
            path,
        )
        self._state = BinaryWorkbenchStateDTO(
            **{
                **state_payload(self._state),
                "directories": {**self._state.directories, action_key: str(path.parent)},
            }
        )
        self.programContextChanged.emit(self._program_context)
        self.stateChanged.emit(self._state)

    def _refresh_tab_label(self, tab_id: str, display_name: str) -> None:
        index = next((idx for idx, tab in enumerate(self._state.tabs) if tab.tab_id == tab_id), -1)
        if index < 0:
            return
        self.setTabText(index, tab_text(display_name))
        self.setTabToolTip(index, display_name)
