from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from src.core.debugger.models.session import DebuggerInstruction
from src.core.debugger.psx_r3000a.control.flow import PsxExecutionTransition


@dataclass(frozen=True)
class DebuggerExecutableRange:
    """Represent one contiguous executable interval from a single origin."""

    start: int
    end_exclusive: int
    origin: str

    def contains(self, address: int) -> bool:
        """Return whether an address belongs to this executable interval."""

        return self.start <= address < self.end_exclusive


def build_executable_ranges(
    instructions: Sequence[DebuggerInstruction],
) -> tuple[DebuggerExecutableRange, ...]:
    """Group instruction metadata by address continuity and source origin."""

    ordered = sorted(instructions, key=lambda item: item.address)
    ranges: list[DebuggerExecutableRange] = []
    for instruction in ordered:
        end = instruction.address + len(instruction.data)
        previous = ranges[-1] if ranges else None
        if (
            previous is not None
            and previous.origin == instruction.origin
            and previous.end_exclusive == instruction.address
        ):
            ranges[-1] = DebuggerExecutableRange(previous.start, end, previous.origin)
        else:
            ranges.append(DebuggerExecutableRange(instruction.address, end, instruction.origin))
    return tuple(ranges)


def entry_executable_range(
    ranges: Sequence[DebuggerExecutableRange],
    initial_pc: int,
) -> DebuggerExecutableRange | None:
    """Return the executable interval containing the restored initial PC."""

    return next((item for item in ranges if item.contains(initial_pc)), None)


def naturally_completed_entry_range(
    entry: DebuggerExecutableRange | None,
    transition: PsxExecutionTransition | None,
    pc: int,
    instruction_addresses: frozenset[int],
) -> bool:
    """Accept only natural fallthrough through the entry interval boundary."""

    return bool(
        entry is not None
        and transition is not None
        and pc == entry.end_exclusive
        and pc not in instruction_addresses
        and entry.contains(transition.source)
        and transition.permits_entry_completion
    )
