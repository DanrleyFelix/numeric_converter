"""Breakpoint entry and filtered metadata table."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QTableWidget, QVBoxLayout, QWidget

from src.core.debugger.contracts.base import BWDebugger
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_hex_offset_validator,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    BREAKPOINT_ADDRESS_PLACEHOLDER,
    BREAKPOINT_FILTER,
    BREAKPOINT_HEADERS,
)
from src.presentation.ui.components.debugger.panels.instruction.highlighting import (
    instruction_cell_delegate,
)
from src.presentation.ui.components.debugger.panels.session.breakpoint.context_menu import (
    show_breakpoint_menu,
)
from src.presentation.ui.components.debugger.panels.session.breakpoint.presentation import (
    BreakpointNameDelegate,
    BreakpointTypeDelegate,
    render_breakpoint_rows,
)
from src.presentation.ui.components.debugger.panels.session.breakpoint.table.editing import (
    add_address_breakpoint,
    navigate_breakpoint_row,
    update_breakpoint_cell,
)
from src.presentation.ui.components.debugger.panels.session.breakpoint.table.where import (
    BreakpointWhereDelegate,
)
from src.presentation.ui.components.debugger.panels.table.columns import (
    CompensatedColumnLayout,
)
from src.presentation.ui.components.debugger.panels.tabs.filter_bar import (
    DebouncedSearchEdit,
)


class DebuggerBreakpointsView(QWidget):
    """Manage breakpoint metadata through Enter, filtering and context actions."""

    navigateRequested = Signal(object)

    def __init__(self, debugger: BWDebugger, parent=None) -> None:
        """Create a joined address entry and compact breakpoint table."""

        super().__init__(parent)
        self._debugger = debugger
        self._filter = ""
        self._refreshing = False
        self.address = QLineEdit(self)
        self.address.setObjectName("debugger-breakpoint-input")
        self.address.setPlaceholderText(BREAKPOINT_ADDRESS_PLACEHOLDER)
        self.address.setFixedHeight(DEBUGGER_LAYOUT.BREAKPOINT_ENTRY_HEIGHT)
        set_hex_offset_validator(self.address)
        self.address.returnPressed.connect(self._add)
        self.search = DebouncedSearchEdit(BREAKPOINT_FILTER, self)
        self.search.setObjectName("debugger-breakpoint-search")
        self.search.setFixedHeight(DEBUGGER_LAYOUT.BREAKPOINT_ENTRY_HEIGHT)
        self.search.filterApplied.connect(self.set_filter)
        self.table = QTableWidget(self)
        self.table.setObjectName("debugger-breakpoints-table")
        self.table.setColumnCount(len(BREAKPOINT_HEADERS))
        self.table.setHorizontalHeaderLabels(BREAKPOINT_HEADERS)
        self._columns = CompensatedColumnLayout(
            self.table,
            DEBUGGER_LAYOUT.BREAKPOINT_COLUMN_MINIMUMS,
            DEBUGGER_LAYOUT.BREAKPOINT_COLUMN_MAXIMUMS,
            DEBUGGER_LAYOUT.BREAKPOINT_GROWTH_COLUMNS,
            DEBUGGER_LAYOUT.BREAKPOINT_COMPENSATION_COLUMNS,
        )
        self.table.setItemDelegateForColumn(
            DEBUGGER_LAYOUT.BREAKPOINT_NAME_COLUMN, BreakpointNameDelegate(self.table)
        )
        self.table.setItemDelegateForColumn(
            DEBUGGER_LAYOUT.BREAKPOINT_TYPE_COLUMN, BreakpointTypeDelegate(self.table)
        )
        self.table.setItemDelegateForColumn(
            DEBUGGER_LAYOUT.BREAKPOINT_WHERE_COLUMN,
            BreakpointWhereDelegate(self.table),
        )
        self.table.setItemDelegateForColumn(
            DEBUGGER_LAYOUT.BREAKPOINT_INSTRUCTION_COLUMN,
            instruction_cell_delegate(self.table),
        )
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(
            DEBUGGER_LAYOUT.LOWER_TABLE_ROW_HEIGHT
        )
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.cellDoubleClicked.connect(self._navigate_row)
        self.table.itemChanged.connect(self._change)
        entry = QWidget(self)
        entry.setObjectName("debugger-breakpoint-entry")
        entry_layout = QHBoxLayout(entry)
        entry_layout.setContentsMargins(0, 0, 0, 0)
        entry_layout.setSpacing(0)
        entry_layout.addWidget(self.address)
        entry_layout.addWidget(self.search, 1)
        divider = QWidget(self)
        divider.setObjectName("debugger-breakpoint-divider")
        divider.setFixedHeight(DEBUGGER_LAYOUT.PANEL_BORDER_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(entry)
        layout.addWidget(divider)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        """Render breakpoint address, instruction and effective state."""

        render_breakpoint_rows(self)

    def fit_columns(self) -> None:
        """Fit breakpoint columns to the reserved scrollbar boundary."""

        self._columns.fit()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep the breakpoint table attached to its vertical scrollbar."""

        super().resizeEvent(event)
        self.fit_columns()

    def set_filter(self, text: str) -> None:
        """Filter visible breakpoints by formatted address characters."""

        self._filter = text.strip().casefold()
        self.refresh()

    def set_entry_width(self, width: int) -> None:
        """Match the address-entry width to the complete tab strip."""

        self.address.setFixedWidth(max(1, width))

    def _add(self) -> None:
        """Add the entered address when Enter is pressed."""

        add_address_breakpoint(self)

    def _change(self, item) -> None:
        """Persist supported edits made to breakpoint metadata cells."""

        update_breakpoint_cell(self, item)

    def _context_menu(self, position) -> None:
        """Offer standard styled breakpoint operations."""

        show_breakpoint_menu(self, position)

    def _navigate_row(self, row: int, _column: int) -> None:
        """Navigate to a double-clicked breakpoint without integer narrowing."""

        navigate_breakpoint_row(self, row)
