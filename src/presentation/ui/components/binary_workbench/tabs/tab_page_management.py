from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QSize, Qt
from PySide6.QtWidgets import QPushButton, QTabBar, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.repository.binary_workbench_workspace.constants import COMMANDS
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
    def _add_tab_page(
        self,
        context: BinaryWorkbenchTabContextDTO,
        *,
        materialize: bool = True,
    ) -> None:
        if not materialize:
            page = QWidget(self)
            page.setObjectName("binary-workbench-lazy-tab-page")
            page.setProperty("tab_id", context.tab_id)
            index = self.addTab(page, tab_text(context.display_name))
            self.setTabToolTip(index, context.display_name)
            self.tabBar().add_close_button(index, self._close_button(page))
            return
        page = self._create_editor_page(context)
        index = self.addTab(page, tab_text(context.display_name))
        self.setTabToolTip(index, context.display_name)
        self.tabBar().add_close_button(index, self._close_button(page))

    def _create_editor_page(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchEditorPage:
        """Materialize one tab only when its editor is actually required."""

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
        page.structuralVersionSaveRequested.connect(
            lambda tab_id=context.tab_id: self.schedule_version_autosave(tab_id)
        )
        page.openLabelTabRequested.connect(self.open_label_tab)
        page.symbolEditRequested.connect(self._edit_symbol_from_editor)
        page.statusWarningRequested.connect(self.statusWarningChanged.emit)
        page.statusErrorRequested.connect(self.statusErrorChanged.emit)
        self._handle_page_context_change(context.tab_id, page.current_context())
        return page

    def _materialize_tab_page(self, index: int) -> BinaryWorkbenchEditorPage | None:
        """Replace an inactive placeholder without materializing sibling tabs."""

        if not 0 <= index < self.count():
            return None
        current = self.widget(index)
        if isinstance(current, BinaryWorkbenchEditorPage):
            return current
        context = self.context_at(index)
        if context is None:
            return None
        text = self.tabText(index)
        tooltip = self.tabToolTip(index)
        page = self._create_editor_page(context)
        blocker = QSignalBlocker(self)
        try:
            self.removeTab(index)
            self.insertTab(index, page, text)
            self.setTabToolTip(index, tooltip)
            self.tabBar().add_close_button(index, self._close_button(page))
            self.setCurrentIndex(index)
        finally:
            del blocker
        if current is not None:
            current.deleteLater()
        return page

    def _close_button(self, page: QWidget) -> QPushButton:
        button = QPushButton("X", self.tabBar())
        button.setObjectName("binary-workbench-tab-close")
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.StrongFocus)
        button.clicked.connect(lambda: self.closeRequested.emit(self.indexOf(page)))
        return button

    def _command_directory(self):
        return self._workspace_repository.environment_directory(COMMANDS)
