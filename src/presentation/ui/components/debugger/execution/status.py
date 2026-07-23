from __future__ import annotations

from src.core.debugger.contracts.base import BWDebugger


def latest_execution_address(debugger: BWDebugger) -> int | None:
    """Return the latest executed or explicitly ignored instruction address."""

    return next(
        (
            event.address
            for event in reversed(debugger.events)
            if event.level == "Execution" and event.address is not None
        ),
        None,
    )
