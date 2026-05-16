from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTabWidget

from src.controllers.binary_workbench_controller import BinaryWorkbenchController
from src.modules.dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchStateDTO,
    ProgramContextDTO,
)
from src.presentation.repository.binary_workbench_workspace import (
    BinaryWorkbenchWorkspaceRepository,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_configuration import (
    TabConfigurationMixin,
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
from src.presentation.ui.components.binary_workbench.tabs.tab_workspace import (
    TabWorkspaceMixin,
)


class BinaryWorkbenchTabs(
    TabStateMixin,
    TabPageManagementMixin,
    TabOpeningMixin,
    TabConfigurationMixin,
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
        self.tabBar().setFocusPolicy(Qt.NoFocus)
        self.tabBar().setDrawBase(False)
        self.setTabsClosable(True)
        self.setDocumentMode(True)
        self._workspace_repository = BinaryWorkbenchWorkspaceRepository(
            workspace_directory or Path.cwd()
        )
        self._preferences = preferences or BinaryWorkbenchPreferencesDTO()
        self._program_context = program_context or ProgramContextDTO()
        self._controller = BinaryWorkbenchController()
        self._state = BinaryWorkbenchStateDTO()
        self.currentChanged.connect(self._sync_active_tab)
        self.tabCloseRequested.connect(self.closeRequested.emit)
        self.load_state(state)

    def preferences(self) -> BinaryWorkbenchPreferencesDTO:
        return self._preferences
