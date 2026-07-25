"""Formatting helpers for bounded debugger log rendering."""

from collections.abc import Iterable

from src.core.debugger.models.session import DebuggerEvent


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
) -> list[str]:
    """Format only events matching the active case-insensitive filter."""

    lines = (debugger_event_line(event) for event in events)
    return [
        line
        for line in lines
        if not filter_text or filter_text in line.casefold()
    ]
