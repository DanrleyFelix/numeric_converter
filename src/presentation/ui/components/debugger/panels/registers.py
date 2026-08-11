from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QKeyEvent, QKeySequence, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.models.session import DebuggerSessionState
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import REGISTER_HEADERS
from src.presentation.ui.components.debugger.panels.register.breakpoint.menu import (
    create_register_breakpoint_action,
    show_register_menu,
)
from src.presentation.ui.components.debugger.panels.register.editing import (
    RegisterValueDelegate,
)
from src.presentation.ui.components.debugger.panels.register.highlighting import (
    register_cell_color,
)
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class DebuggerRegisterPanel(QTableWidget):
    """Display, compare and edit registers exposed by `BWDebuggerRegs`."""

    breakpointAdded = Signal()

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
        self.setMinimumWidth(0)
        self.setMaximumWidth(DEBUGGER_LAYOUT.REGISTER_PANEL_MAX_WIDTH)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setCursor(Qt.ArrowCursor)
        self.viewport().setCursor(Qt.ArrowCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)
        self._add_breakpoint_action = create_register_breakpoint_action(self)
        self.addAction(self._add_breakpoint_action)
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
                    item.setTextAlignment(Qt.AlignCenter)
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
        """Keep Reg fixed and distribute remaining width across value columns."""

        widths = list(DEBUGGER_LAYOUT.REGISTER_COLUMN_WIDTHS)
        available = self.viewport().width() - DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
        remaining = max(0, available - sum(widths))
        widths[1] += remaining // 3
        widths[2] += remaining - remaining // 3
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
        """Offer standard Copy and Add Breakpoint register actions."""

        show_register_menu(self, position)
