from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget

from src.modules.dtos import (
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.factory import (
    create_assembly_tab,
    create_binary_tab,
    create_internal_tab,
    create_scratch_tab,
    restorable_state,
)


class BinaryWorkbenchTabs(QTabWidget):
    stateChanged = Signal(object)
    statusChanged = Signal(str)

    def __init__(self, state: BinaryWorkbenchStateDTO) -> None:
        super().__init__()
        self.setObjectName("binary-workbench-tabs")
        self.tabBar().setObjectName("binary-workbench-tab-bar")
        self.setTabsClosable(True)
        self.setDocumentMode(True)
        self._state = BinaryWorkbenchStateDTO()
        self.currentChanged.connect(self._sync_active_tab)
        self.tabCloseRequested.connect(self._close_tab)
        self.load_state(state)

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

    def open_binary_path(self, path: Path) -> None:
        self._append_tab(create_binary_tab(self._state, path))

    def open_assembly_path(self, path: Path) -> None:
        self._append_tab(create_assembly_tab(self._state, path))

    def new_scratch_tab(self) -> None:
        self._append_tab(create_scratch_tab(self._state))

    def open_internal_tab(self) -> None:
        current = self.current_context()
        if current is None or not current.source_path:
            self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_SOURCE_REQUIRED)
            return
        self._append_tab(create_internal_tab(self._state, current))

    def set_current_cpu_arch(self, value: str) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.set_cpu_arch(value)

    def current_context(self) -> BinaryWorkbenchTabContextDTO | None:
        index = self.currentIndex()
        return self._state.tabs[index] if 0 <= index < len(self._state.tabs) else None

    def _append_tab(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._state = BinaryWorkbenchStateDTO(
            tabs=[*self._state.tabs, context],
            active_tab_id=context.tab_id,
            share_view_preferences=self._state.share_view_preferences,
        )
        self._add_tab_page(context)
        self.setCurrentIndex(self.count() - 1)
        self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_OPENED_TEMPLATE.format(name=context.display_name))
        self.stateChanged.emit(self._state)

    def _add_tab_page(self, context: BinaryWorkbenchTabContextDTO) -> None:
        page = BinaryWorkbenchEditorPage(context)
        page.contextChanged.connect(lambda updated, tab_id=context.tab_id: self._replace_context(tab_id, updated))
        self.addTab(page, context.display_name)

    def _close_tab(self, index: int) -> None:
        if not 0 <= index < len(self._state.tabs):
            return
        closed = self._state.tabs[index]
        remaining = [tab for idx, tab in enumerate(self._state.tabs) if idx != index]
        self.removeTab(index)
        self._state = BinaryWorkbenchStateDTO(
            tabs=remaining,
            active_tab_id=remaining[min(index, len(remaining) - 1)].tab_id if remaining else None,
            share_view_preferences=self._state.share_view_preferences,
        )
        self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_CLOSED_TEMPLATE.format(name=closed.display_name))
        self.stateChanged.emit(self._state)

    def _replace_context(self, tab_id: str, context: object) -> None:
        if not isinstance(context, BinaryWorkbenchTabContextDTO):
            return
        self._state = BinaryWorkbenchStateDTO(
            tabs=[context if tab.tab_id == tab_id else tab for tab in self._state.tabs],
            active_tab_id=self._state.active_tab_id,
            share_view_preferences=self._state.share_view_preferences,
        )
        self.stateChanged.emit(self._state)

    def _sync_active_tab(self, index: int) -> None:
        if not 0 <= index < len(self._state.tabs):
            return
        self._state = BinaryWorkbenchStateDTO(
            tabs=self._state.tabs,
            active_tab_id=self._state.tabs[index].tab_id,
            share_view_preferences=self._state.share_view_preferences,
        )
        self.stateChanged.emit(self._state)

    def _active_index(self) -> int:
        return next(
            (idx for idx, tab in enumerate(self._state.tabs) if tab.tab_id == self._state.active_tab_id),
            0,
        )
