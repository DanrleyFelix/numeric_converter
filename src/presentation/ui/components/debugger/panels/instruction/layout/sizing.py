"""Deterministic instruction-table column sizing."""

from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT


def resize_instruction_columns(table) -> None:
    """Fill the viewport while preserving fixed columns and the scrollbar gap."""

    fixed_width = (
        DEBUGGER_LAYOUT.INSTRUCTION_NUMBER_MIN_WIDTH
        + DEBUGGER_LAYOUT.RAW_INSTRUCTION_WIDTH
        + DEBUGGER_LAYOUT.INSTRUCTION_ORIGIN_MIN_WIDTH
        + DEBUGGER_LAYOUT.INSTRUCTION_STATUS_WIDTH
    )
    target = max(
        sum(DEBUGGER_LAYOUT.INSTRUCTION_COLUMN_MINIMUMS),
        table.viewport().width() - DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP,
    )
    flexible_minimum = (
        DEBUGGER_LAYOUT.INSTRUCTION_ADDRESS_MIN_WIDTH
        + DEBUGGER_LAYOUT.INSTRUCTION_BYTES_MIN_WIDTH
    )
    flexible_width = max(flexible_minimum, target - fixed_width)
    flexible_extra = flexible_width - flexible_minimum
    address_width = (
        DEBUGGER_LAYOUT.INSTRUCTION_ADDRESS_MIN_WIDTH
        + flexible_extra // 2
    )
    bytes_width = (
        DEBUGGER_LAYOUT.INSTRUCTION_BYTES_MIN_WIDTH
        + flexible_extra - flexible_extra // 2
    )
    widths = (
        DEBUGGER_LAYOUT.INSTRUCTION_NUMBER_MIN_WIDTH,
        address_width,
        bytes_width,
        DEBUGGER_LAYOUT.RAW_INSTRUCTION_WIDTH,
        DEBUGGER_LAYOUT.INSTRUCTION_ORIGIN_MIN_WIDTH,
        DEBUGGER_LAYOUT.INSTRUCTION_STATUS_WIDTH,
    )
    for column, width in enumerate(widths):
        table.setColumnWidth(column, width)
