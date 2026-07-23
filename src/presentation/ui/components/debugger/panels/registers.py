from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QKeyEvent, QKeySequence, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
)

from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.models.session import DebuggerSessionState
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import REGISTER_HEADERS
from src.presentation.ui.components.debugger.panels.register.editing import (
    RegisterValueDelegate,
)
from src.presentation.ui.components.debugger.panels.register.highlighting import (
    register_cell_color,
)
from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class DebuggerRegisterPanel(QTableWidget):
    """Display, compare and edit registers exposed by `BWDebuggerRegs`."""

    def __init__(self, debugger: BWDebugger, parent=None) -> None:
        """Create a register table bound to one debugger session."""

        super().__init__(parent)
        self._debugger = debugger
        self._snapshot: dict[str, int] = {}
        self._refreshing = False
        self.setObjectName("debugger-registers")
        self.setColumnCount(len(REGISTER_HEADERS))
        self.setHorizontalHeaderLabels(REGISTER_HEADERS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.setItemDelegateForColumn(1, RegisterValueDelegate("hexadecimal", self))
        self.setItemDelegateForColumn(2, RegisterValueDelegate("decimal", self))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMaximumWidth(DEBUGGER_LAYOUT.REGISTER_PANEL_MAX_WIDTH)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)
        self.itemChanged.connect(self._edit_register)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(DEBUGGER_LAYOUT.REGISTER_ROW_HEIGHT)
        self._resize_columns()

    def refresh(self) -> None:
        """Render current values and mark registers changed since the last refresh."""

        values = self._debugger.registers.snapshot()
        descriptors = tuple(
            descriptor
            for descriptor in self._debugger.registers.descriptors
            if descriptor.name != "zero"
        )
        self._refreshing = True
        try:
            self.setRowCount(len(descriptors))
            editable = self._debugger.state in {
                DebuggerSessionState.READY,
                DebuggerSessionState.PAUSED,
            }
            for row, descriptor in enumerate(descriptors):
                value = values[descriptor.name]
                changed = descriptor.name in self._snapshot and self._snapshot[descriptor.name] != value
                entries = (descriptor.name, f"0x{value:08X}", str(value))
                for column, text in enumerate(entries):
                    item = QTableWidgetItem(text)
                    flags = item.flags()
                    if column not in {1, 2} or not editable:
                        flags &= ~Qt.ItemIsEditable
                    item.setFlags(flags)
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    color = register_cell_color(column, text)
                    if color:
                        item.setForeground(QColor(color))
                    if changed:
                        item.setBackground(QColor(THEME_TOKENS["bg-control-checked-hover"]))
                    self.setItem(row, column, item)
        finally:
            self._refreshing = False
        self._snapshot = values

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Distribute available width with Decimal then Hexadecimal priority."""

        super().resizeEvent(event)
        self._resize_columns()

    def _resize_columns(self) -> None:
        """Keep every register column inside its declared width limits."""

        limits = DEBUGGER_LAYOUT.REGISTER_COLUMN_LIMITS
        widths = [minimum for minimum, _maximum in limits]
        remaining = max(0, self.viewport().width() - sum(widths))
        for column in (2, 1, 0):
            growth = min(remaining, limits[column][1] - widths[column])
            widths[column] += growth
            remaining -= growth
        for column, width in enumerate(widths):
            self.setColumnWidth(column, width)

    def _edit_register(self, item: QTableWidgetItem) -> None:
        """Apply user edits only while the debugger is paused."""

        if self._refreshing or item.column() not in {1, 2}:
            return
        if self._debugger.state not in {
            DebuggerSessionState.READY,
            DebuggerSessionState.PAUSED,
        }:
            self.refresh()
            return
        name_item = self.item(item.row(), 0)
        try:
            value = int(item.text(), 16 if item.column() == 1 else 10)
            self._debugger.registers.write(name_item.text(), value)
        except (ValueError, AttributeError):
            pass
        self.refresh()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Copy the current register cell with the standard shortcut."""

        if event.matches(QKeySequence.Copy) and self.currentItem() is not None:
            QApplication.clipboard().setText(self.currentItem().text())
            event.accept()
            return
        super().keyPressEvent(event)

    def _open_context_menu(self, position) -> None:
        """Offer copying for the register value under the pointer."""

        item = self.itemAt(position)
        if item is None:
            return
        menu = QMenu(self)
        menu.setObjectName("binary-workbench-editor-context-menu")
        copy_action = QAction("Copy", menu)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(item.text()))
        menu.addAction(copy_action)
        use_white_menu_icons(menu)
        menu.exec(self.viewport().mapToGlobal(position))
