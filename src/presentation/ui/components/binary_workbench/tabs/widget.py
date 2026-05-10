from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTabWidget

from src.modules.dtos import BinaryWorkbenchStateDTO
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


class BinaryWorkbenchTabs(
    TabStateMixin,
    TabPageManagementMixin,
    TabOpeningMixin,
    TabConfigurationMixin,
    TabLibrariesMixin,
    TabVersionsMixin,
    TabFileSavingMixin,
    TabNavigationSearchMixin,
    QTabWidget,
):
    stateChanged = Signal(object)
    statusChanged = Signal(str)
    closeRequested = Signal(int)

    def __init__(self, state: BinaryWorkbenchStateDTO) -> None:
        super().__init__()
        self.setObjectName("binary-workbench-tabs")
        self.setFocusPolicy(Qt.NoFocus)
        self.setTabBar(BinaryWorkbenchTabBar())
        self.tabBar().setObjectName("binary-workbench-tab-bar")
        self.tabBar().setFocusPolicy(Qt.NoFocus)
        self.tabBar().setDrawBase(False)
        self.setTabsClosable(True)
        self.setDocumentMode(True)
        self._state = BinaryWorkbenchStateDTO()
        self.currentChanged.connect(self._sync_active_tab)
        self.tabCloseRequested.connect(self.closeRequested.emit)
        self.load_state(state)
