from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QPushButton, QTabBar

from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import tab_text


class BinaryWorkbenchTabBar(QTabBar):
    def tabSizeHint(self, index: int) -> QSize:
        return QSize(BINARY_WORKBENCH_LAYOUT.TAB_MAX_WIDTH, BINARY_WORKBENCH_LAYOUT.TAB_MIN_HEIGHT)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_close_buttons()

    def tabLayoutChange(self) -> None:
        super().tabLayoutChange()
        self._position_close_buttons()

    def _position_close_buttons(self) -> None:
        for index in range(self.count()):
            button = self.tabButton(index, QTabBar.RightSide)
            if button is None:
                continue
            rect = self.tabRect(index)
            size = BINARY_WORKBENCH_LAYOUT.TAB_CLOSE_BUTTON_SIZE
            button.setFixedSize(size, size)
            button.move(rect.right() - size - 4, rect.top() + 2)


class TabPageManagementMixin:
    def _add_tab_page(self, context: BinaryWorkbenchTabContextDTO) -> None:
        page = BinaryWorkbenchEditorPage(context, self._preferences)
        page.contextChanged.connect(lambda updated, tab_id=context.tab_id: self._replace_context(tab_id, updated))
        index = self.addTab(page, tab_text(context.display_name))
        self.setTabToolTip(index, context.display_name)
        self.tabBar().setTabButton(index, QTabBar.RightSide, self._close_button(page))

    def _close_button(self, page: BinaryWorkbenchEditorPage) -> QPushButton:
        button = QPushButton("X", self.tabBar())
        button.setObjectName("binary-workbench-tab-close")
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)
        button.clicked.connect(lambda: self.closeRequested.emit(self.indexOf(page)))
        return button
