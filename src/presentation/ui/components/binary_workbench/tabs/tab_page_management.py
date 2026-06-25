from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QPushButton, QTabBar

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_STATE
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import tab_text


class BinaryWorkbenchTabBar(QTabBar):
    def __init__(self) -> None:
        super().__init__()
        self._close_buttons: list[QPushButton] = []

    def tabSizeHint(self, index: int) -> QSize:
        return QSize(BINARY_WORKBENCH_LAYOUT.TAB_MAX_WIDTH, BINARY_WORKBENCH_LAYOUT.TAB_MIN_HEIGHT)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_close_buttons()

    def tabLayoutChange(self) -> None:
        super().tabLayoutChange()
        self._position_close_buttons()

    def tabRemoved(self, index: int) -> None:
        self.remove_close_button(index)

    def add_close_button(self, index: int, button: QPushButton) -> None:
        button.setParent(self)
        self._close_buttons.insert(index, button)
        self._position_close_buttons()

    def remove_close_button(self, index: int) -> None:
        if not 0 <= index < len(self._close_buttons):
            return
        self._close_buttons.pop(index).deleteLater()
        self._position_close_buttons()

    def sync_close_button_order(self, source: int, target: int) -> None:
        if not 0 <= source < len(self._close_buttons) or not 0 <= target < len(self._close_buttons):
            return
        button = self._close_buttons.pop(source)
        self._close_buttons.insert(target, button)
        self._position_close_buttons()

    def close_button(self, index: int) -> QPushButton | None:
        return self._close_buttons[index] if 0 <= index < len(self._close_buttons) else None

    def _position_close_buttons(self) -> None:
        for index, button in enumerate(self._close_buttons):
            if index >= self.count():
                button.hide()
                continue
            rect = self.tabRect(index)
            size = BINARY_WORKBENCH_LAYOUT.TAB_CLOSE_BUTTON_SIZE
            button.setFixedSize(size, size)
            button.move(
                rect.right() - size - BINARY_WORKBENCH_LAYOUT.TAB_CLOSE_BUTTON_RIGHT_INSET + 1,
                rect.top() + BINARY_WORKBENCH_LAYOUT.TAB_CLOSE_BUTTON_TOP_INSET,
            )
            button.show()
            button.raise_()


class TabPageManagementMixin:
    def _add_tab_page(self, context: BinaryWorkbenchTabContextDTO) -> None:
        context = self._workspace_context_for_page(context)
        self._replace_context_without_emit(context.tab_id, context)
        page = BinaryWorkbenchEditorPage(
            context,
            self._preferences,
            self._command_directory(),
        )
        page.contextChanged.connect(
            lambda updated, tab_id=context.tab_id: self._handle_page_context_change(
                tab_id,
                updated,
            )
        )
        page.openLabelTabRequested.connect(self.open_label_tab)
        page.statusWarningRequested.connect(self.statusWarningChanged.emit)
        index = self.addTab(page, tab_text(context.display_name))
        self.setTabToolTip(index, context.display_name)
        self.tabBar().add_close_button(index, self._close_button(page))
        self._handle_page_context_change(context.tab_id, page.current_context())

    def _close_button(self, page: BinaryWorkbenchEditorPage) -> QPushButton:
        button = QPushButton("X", self.tabBar())
        button.setObjectName("binary-workbench-tab-close")
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)
        button.clicked.connect(lambda: self.closeRequested.emit(self.indexOf(page)))
        return button

    def _command_directory(self):
        directory = self._state.directories.get(BINARY_WORKBENCH_STATE.COMMANDS_DIRECTORY)
        if directory:
            return Path(directory)
        return self._workspace_repository.directory.parent / "commands"
