from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QTabWidget, QToolButton, QWidget

from src.controllers.binary_workbench_controller import BinaryWorkbenchController
from src.modules.application_dtos import ProgramContextDTO
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchStateDTO,
)
from src.presentation.repository.binary_workbench_workspace import (
    BinaryWorkbenchWorkspaceRepository,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_configuration import (
    TabConfigurationMixin,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_commands import (
    TabCommandsMixin,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_file_saving import (
    TabFileSavingMixin,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_libraries import TabLibrariesMixin
from src.presentation.ui.components.binary_workbench.tabs.tab_navigation_search import (
    TabNavigationSearchMixin,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_opening import TabOpeningMixin
from src.presentation.ui.components.binary_workbench.tabs.tab_page_management import (
    BinaryWorkbenchTabBar,
    TabPageManagementMixin,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_state import TabStateMixin
from src.presentation.ui.components.binary_workbench.tabs.tab_versions import TabVersionsMixin
from src.presentation.ui.components.binary_workbench.tabs.tab_view_configuration import (
    TabViewConfigurationMixin,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_workspace import (
    TabWorkspaceMixin,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)


class BinaryWorkbenchTabs(
    TabStateMixin,
    TabPageManagementMixin,
    TabOpeningMixin,
    TabConfigurationMixin,
    TabViewConfigurationMixin,
    TabCommandsMixin,
    TabLibrariesMixin,
    TabVersionsMixin,
    TabWorkspaceMixin,
    TabFileSavingMixin,
    TabNavigationSearchMixin,
    QTabWidget,
):
    stateChanged = Signal(object)
    preferencesChanged = Signal(object)
    programContextChanged = Signal(object)
    statusChanged = Signal(str)
    statusWarningChanged = Signal(str)
    closeRequested = Signal(int)

    def __init__(
        self,
        state: BinaryWorkbenchStateDTO,
        workspace_directory: Path | None = None,
        preferences: BinaryWorkbenchPreferencesDTO | None = None,
        program_context: ProgramContextDTO | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("binary-workbench-tabs")
        self.setFocusPolicy(Qt.NoFocus)
        self.setTabBar(BinaryWorkbenchTabBar())
        self.tabBar().setObjectName("binary-workbench-tab-bar")
        self.tabBar().setFocusPolicy(Qt.StrongFocus)
        self.tabBar().setDrawBase(False)
        self.tabBar().setUsesScrollButtons(False)
        self.tabBar().setMovable(True)
        self._build_tab_navigation()
        self.setTabsClosable(True)
        self.setDocumentMode(True)
        self._workspace_repository = BinaryWorkbenchWorkspaceRepository(
            workspace_directory or Path.cwd()
        )
        self._preferences = preferences or BinaryWorkbenchPreferencesDTO()
        self._program_context = program_context or ProgramContextDTO()
        self._controller = BinaryWorkbenchController()
        self._state = BinaryWorkbenchStateDTO()
        self._stale_context_pages: set[str] = set()
        self.currentChanged.connect(self._sync_active_tab)
        self.currentChanged.connect(lambda _: self._update_tab_navigation())
        self.tabBar().tabMoved.connect(self._sync_tab_order)
        self.tabCloseRequested.connect(self.closeRequested.emit)
        self.load_state(state)

    def preferences(self) -> BinaryWorkbenchPreferencesDTO:
        return self._preferences

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        self._update_tab_navigation()

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        self._update_tab_navigation()

    def _build_tab_navigation(self) -> None:
        shell = QWidget(self)
        shell.setObjectName("binary-workbench-tab-nav")
        layout = QHBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.TAB_NAV_SPACING)
        self._previous_tab_button = self._tab_navigation_button("<", BINARY_WORKBENCH_TEXT.PREVIOUS_TAB)
        self._next_tab_button = self._tab_navigation_button(">", BINARY_WORKBENCH_TEXT.NEXT_TAB)
        self._previous_tab_button.clicked.connect(lambda: self._move_current_tab(-1))
        self._next_tab_button.clicked.connect(lambda: self._move_current_tab(1))
        layout.addWidget(self._previous_tab_button)
        layout.addWidget(self._next_tab_button)
        self.setCornerWidget(shell, Qt.TopRightCorner)

    def _tab_navigation_button(self, text: str, tooltip: str) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName("binary-workbench-tab-nav-button")
        button.setText(text)
        button.setToolTip(tooltip)
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)
        button.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.TAB_NAV_BUTTON_WIDTH,
            BINARY_WORKBENCH_LAYOUT.TAB_NAV_BUTTON_HEIGHT,
        )
        return button

    def _move_current_tab(self, step: int) -> None:
        target = self.currentIndex() + step
        if 0 <= target < self.count():
            self.setCurrentIndex(target)

    def _update_tab_navigation(self) -> None:
        if not hasattr(self, "_previous_tab_button"):
            return
        index = self.currentIndex()
        self._previous_tab_button.setEnabled(index > 0)
        self._next_tab_button.setEnabled(0 <= index < self.count() - 1)
