"""Runtime breakpoint transitions around one emulated instruction."""

from dataclasses import replace

from src.core.debugger.breakpoints.conditions import parse_register_condition
from src.core.debugger.breakpoints.types import REGISTER_BREAKPOINT_TYPE
from src.core.debugger.models.session import DebuggerBreakpoint, DebuggerEvent


class PsxExecutionBreakpointMixin:
    """Detect access and register hits caused by the current instruction."""

    def _prepare_breakpoint_step(self) -> None:
        """Reset transient hit state before Unicorn executes one instruction."""

        self._pending_breakpoint_identifier = None
        self._breakpoint_hit_during_step = False

    def _queue_memory_breakpoint(self, breakpoint: DebuggerBreakpoint) -> None:
        """Retain the first memory breakpoint observed during this step."""

        if self._pending_breakpoint_identifier is None:
            self._pending_breakpoint_identifier = breakpoint.identifier

    def _complete_breakpoint_step(
        self,
        instruction_address: int,
        before: dict[str, int],
        after: dict[str, int],
    ) -> None:
        """Resolve memory hits first, then false-to-true register conditions."""

        identifier = self._pending_breakpoint_identifier
        if identifier is None:
            register_breakpoint = self._matching_register_breakpoint(before, after)
            identifier = (
                register_breakpoint.identifier
                if register_breakpoint is not None
                else None
            )
        if identifier is None:
            return
        self._mark_breakpoint_hit(identifier, instruction_address)
        self._breakpoint_hit_during_step = True

    def _matching_register_breakpoint(
        self,
        before: dict[str, int],
        after: dict[str, int],
    ) -> DebuggerBreakpoint | None:
        """Return the first register condition becoming true in this step."""

        for breakpoint in self._breakpoints.values():
            if (
                breakpoint.breakpoint_type != REGISTER_BREAKPOINT_TYPE
                or not breakpoint.enabled
                or not breakpoint.valid
            ):
                continue
            condition = parse_register_condition(
                breakpoint.where, self._register_aliases
            )
            if not condition.evaluate(before) and condition.evaluate(after):
                return breakpoint
        return None

    def _mark_breakpoint_hit(
        self,
        identifier: int,
        instruction_address: int,
    ) -> None:
        """Persist the causative instruction and emit one breakpoint event."""

        breakpoint = self._breakpoints.get(identifier)
        if breakpoint is None:
            return
        instruction = self._instruction_at(instruction_address)
        raw_instruction = (
            instruction.raw_instruction
            if instruction is not None
            else "Instruction executed"
        )
        self._breakpoints[identifier] = replace(
            breakpoint,
            triggered=True,
            hit_instruction=raw_instruction,
        )
        self._events.append(
            DebuggerEvent(
                "Info",
                f"Breakpoint reached at 0x{instruction_address:08X}.",
                instruction_address,
                {"breakpoint": identifier, "where": breakpoint.where},
            )
        )

    def _clear_breakpoint_hits(self) -> None:
        """Return triggered breakpoints to Enabled while retaining hit details."""

        for identifier, breakpoint in tuple(self._breakpoints.items()):
            if breakpoint.triggered:
                self._breakpoints[identifier] = replace(
                    breakpoint, triggered=False
                )
