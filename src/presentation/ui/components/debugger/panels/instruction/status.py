"""Instruction status selection independent from Qt rendering."""

from src.core.debugger.contracts.base import BWDebugger


def instruction_status(
    debugger: BWDebugger,
    address: int,
    pc: int,
    last_pc: int | None,
    stored_status: str,
) -> str:
    """Return the display status for one instruction address."""

    executions = debugger.statistics.executed.get(address, 0)
    if executions:
        return f"EXEC ({executions})"
    if address == pc:
        return "ACTUAL"
    if stored_status != "Ready":
        return stored_status
    if last_pc is not None and address == last_pc:
        return "LAST"
    if address in debugger.ignored_instructions or address in debugger.ignored_addresses:
        hits = debugger.statistics.ignored.get(address, 0)
        return f"IGNORED ({hits})"
    if any(item.address == address and item.enabled for item in debugger.breakpoints):
        return "Breakpoint"
    return "READY"
