"""Breakpoint table creation, editing and navigation actions."""

from PySide6.QtCore import Qt

from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT


def add_address_breakpoint(view) -> None:
    """Create a default execution breakpoint from the hexadecimal entry."""

    if not view.address.hasAcceptableInput():
        return
    text = view.address.text().strip()
    try:
        address = int(text, 0 if text.lower().startswith("0x") else 16)
    except ValueError:
        return
    view._debugger.add_breakpoint(address)
    view.address.clear()
    view.refresh()


def update_breakpoint_cell(view, item) -> None:
    """Persist editable Name and Type cells through the debugger contract."""

    if view._refreshing:
        return
    identifier = int(item.data(Qt.UserRole))
    if item.column() == DEBUGGER_LAYOUT.BREAKPOINT_NAME_COLUMN:
        view._debugger.set_breakpoint_name(identifier, item.text())
    elif item.column() == DEBUGGER_LAYOUT.BREAKPOINT_TYPE_COLUMN:
        try:
            view._debugger.set_breakpoint_type(identifier, item.text())
        except ValueError:
            pass
    else:
        return
    view.refresh()


def navigate_breakpoint_row(view, row: int) -> None:
    """Navigate only address-based breakpoints and ignore register conditions."""

    item = view.table.item(row, DEBUGGER_LAYOUT.BREAKPOINT_WHERE_COLUMN)
    address = item.data(Qt.UserRole + 1) if item is not None else None
    if address is not None:
        view.navigateRequested.emit(int(address))
