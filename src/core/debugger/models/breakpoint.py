"""Typed debugger breakpoint metadata."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DebuggerBreakpoint:
    """Represent one typed non-invasive debugger breakpoint."""

    address: int | None
    enabled: bool = True
    origin: str = ""
    instruction: str = ""
    valid: bool = True
    name: str = ""
    breakpoint_type: str = "execution"
    where: str = ""
    identifier: int = 0
    hit_instruction: str = ""
    triggered: bool = False
