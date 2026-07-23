"""Breakpoint state labels, colors and column sizing."""

from src.core.debugger.models.session import DebuggerSessionState
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


def breakpoint_status(debugger, breakpoint) -> str:
    """Return Enabled, Disabled, Triggered or Invalid."""

    if not breakpoint.valid:
        return "Invalid"
    if (
        breakpoint.enabled
        and debugger.state == DebuggerSessionState.PAUSED
        and debugger.pc == breakpoint.address
    ):
        return "Triggered"
    return "Enabled" if breakpoint.enabled else "Disabled"


def breakpoint_status_color(status: str) -> str:
    """Return the established state color for one breakpoint status."""

    if status == "Enabled":
        return THEME_TOKENS["text-success"]
    if status == "Triggered":
        return THEME_TOKENS["text-warning"]
    return THEME_TOKENS["text-danger"]


def resize_breakpoint_columns(table) -> None:
    """Apply stable width adjustments without cumulative growth."""

    for column, adjustment in enumerate(
        DEBUGGER_LAYOUT.BREAKPOINT_COLUMN_ADJUSTMENTS
    ):
        table.resizeColumnToContents(column)
        table.setColumnWidth(column, max(40, table.columnWidth(column) + adjustment))
