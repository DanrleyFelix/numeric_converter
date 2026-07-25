"""Formatting helpers for bounded debugger log rendering."""

from collections.abc import Collection, Iterable

from src.core.debugger.models.session import DebuggerEvent
from src.presentation.ui.components.debugger.constants.texts import (
    CONFIG_LOG_LEVELS,
)


def debugger_event_line(event: DebuggerEvent) -> str:
    """Format one event while avoiding redundant Memory and Info addresses."""

    show_address = (
        event.address is not None
        and event.level not in {"Memory", "Info"}
    )
    address = f" [0x{event.address:08X}]" if show_address else ""
    return f"{event.level}{address}: {event.message}"


def debugger_event_lines(
    events: Iterable[DebuggerEvent],
    filter_text: str,
    enabled_levels: Collection[str] | None = None,
) -> list[str]:
    """Format only events matching the active case-insensitive filter."""

    selected = set(CONFIG_LOG_LEVELS if enabled_levels is None else enabled_levels)
    lines = (
        debugger_event_line(event)
        for event in events
        if debugger_event_category(event) in selected
    )
    return [
        line
        for line in lines
        if not filter_text or filter_text in line.casefold()
    ]


def debugger_event_category(event: DebuggerEvent) -> str:
    """Map specialized event levels to one configurable log category."""

    if event.level in CONFIG_LOG_LEVELS:
        return event.level
    return "Error" if "error" in event.level.casefold() else "Info"
