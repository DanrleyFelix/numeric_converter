"""Instruction status selection independent from Qt rendering."""

from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.models.session import DebuggerSessionState


def instruction_status(
    debugger: BWDebugger,
    address: int,
    pc: int,
    last_pc: int | None,
    stored_status: str,
) -> str:
    """Return the display status for one instruction address."""

    if address in debugger.ignored_instructions or address in debugger.ignored_addresses:
        hits = debugger.statistics.ignored.get(address, 0)
        return f"IGNORED ({hits})"
    breakpoint = next(
        (item for item in debugger.breakpoints if item.address == address), None
    )
    if (
        breakpoint is not None
        and breakpoint.enabled
        and debugger.state == DebuggerSessionState.PAUSED
        and address == pc
    ):
        return "BREAK"
    if breakpoint is not None:
        return "BREAKPOINT"
    executions = debugger.statistics.executed.get(address, 0)
    if executions:
        return f"EXEC ({executions})"
    if address == pc:
        return "ACTUAL"
    if stored_status != "Ready":
        return stored_status.upper()
    if last_pc is not None and address == last_pc:
        return "LAST"
    return "READY"
