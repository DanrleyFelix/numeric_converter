from __future__ import annotations

from time import monotonic, sleep

from src.core.debugger.models.session import (
    DebuggerError,
    DebuggerEvent,
    DebuggerSessionState,
)
from src.core.debugger.execution.constants import (
    MAX_EXECUTION_INTERVAL_MS,
    MIN_EXECUTION_INTERVAL_MS,
)
from src.core.debugger.psx_r3000a.control.flow import decode_control_flow
from src.core.debugger.psx_r3000a.execution.running.constants import (
    DEFAULT_EXECUTION_LIMIT,
    EXECUTION_POLL_INTERVAL_SECONDS,
)


class PsxRunSessionMixin:
    """Provide cooperative continuous execution and Step Over control."""

    @property
    def execution_interval_ms(self) -> int:
        """Return the configured delay between automatic instructions."""

        return self._execution_interval_ms

    def set_execution_interval(self, interval_ms: int) -> None:
        """Set a validated automatic execution interval in milliseconds."""

        if not MIN_EXECUTION_INTERVAL_MS <= interval_ms <= MAX_EXECUTION_INTERVAL_MS:
            raise ValueError("Execution interval is outside the supported range.")
        self._execution_interval_ms = interval_ms

    def run(self, limit: int | None = None) -> None:
        """Run from the current PC until pause, stop, breakpoint or limit."""

        if self._state not in {DebuggerSessionState.READY, DebuggerSessionState.PAUSED}:
            raise self._state_error("run")
        self._clear_breakpoint_hits()
        resume_breakpoint = (
            self._state == DebuggerSessionState.PAUSED
            and self._active_breakpoint(self.pc) is not None
        )
        self._run_loop(
            DEFAULT_EXECUTION_LIMIT if limit is None else max(1, limit),
            bypass_first_breakpoint=resume_breakpoint,
        )

    def pause(self) -> None:
        """Request a cooperative pause that preserves all volatile state."""

        if self._state != DebuggerSessionState.RUNNING:
            raise self._state_error("pause")
        self._pause_requested = True

    def stop(self) -> None:
        """Stop execution and require Restart before another execution."""

        self._stop_requested = True
        self._state = DebuggerSessionState.STOPPED
        self._events.append(DebuggerEvent("Info", "Debugger session stopped."))

    def step_over(self, limit: int | None = None) -> None:
        """Step normally or run a call until its local return address."""

        if self._state not in {DebuggerSessionState.READY, DebuggerSessionState.PAUSED}:
            raise self._state_error("step over")
        self._clear_breakpoint_hits()
        try:
            data = self.read_memory(self.pc, self.step_rules.instruction_size)
            flow = decode_control_flow(data, self.pc, self._registers.snapshot())
        except DebuggerError as error:
            self._fail(error)
            raise
        if flow is None or not flow.is_call:
            self.step()
            return
        return_address = self.pc + self.step_rules.instruction_size * 2
        budget = DEFAULT_EXECUTION_LIMIT if limit is None else max(1, limit)
        self._run_loop(budget, return_address, True)

    def _run_loop(
        self,
        limit: int,
        return_address: int | None = None,
        bypass_first_breakpoint: bool = False,
    ) -> None:
        """Run logical instructions with cooperative stop conditions."""

        self._pause_requested = False
        self._stop_requested = False
        self._state = DebuggerSessionState.RUNNING
        for index in range(max(1, limit)):
            if self._finish_requested():
                return
            breakpoint = self._active_breakpoint(self.pc)
            if breakpoint is not None and not (index == 0 and bypass_first_breakpoint):
                self._mark_breakpoint_hit(breakpoint.identifier, self.pc)
                self._state = DebuggerSessionState.PAUSED
                return
            if return_address is not None and index and self.pc == return_address:
                self._state = DebuggerSessionState.PAUSED
                return
            try:
                self._execute_current()
            except DebuggerError as error:
                self._fail(error)
                # Execution faults are part of the debugger state, not worker
                # failures.  Keeping them inside the session lets packaged
                # builds retain the window and present the Error event in the
                # Debug Log instead of unwinding through the QThread boundary.
                return
            if self._breakpoint_hit_during_step:
                self._state = DebuggerSessionState.PAUSED
                return
            if self._finish_at_program_end():
                return
            if self._wait_execution_interval():
                return
        self._events.append(DebuggerEvent("Warning", f"Execution safety limit reached: {limit}."))
        self._state = DebuggerSessionState.PAUSED

    def _wait_execution_interval(self) -> bool:
        """Wait cooperatively for pacing while honoring Pause and Stop."""

        if self._execution_interval_ms <= 0:
            return False
        deadline = monotonic() + self._execution_interval_ms / 1000
        while monotonic() < deadline:
            if self._finish_requested():
                return True
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            sleep(min(EXECUTION_POLL_INTERVAL_SECONDS, remaining))
        return False

    def _finish_requested(self) -> bool:
        """Apply pending Pause or Stop requests between instructions."""

        if self._stop_requested:
            self._state = DebuggerSessionState.STOPPED
            return True
        if self._pause_requested:
            self._pause_requested = False
            self._state = DebuggerSessionState.PAUSED
            self._events.append(DebuggerEvent("Info", "Debugger session paused."))
            return True
        return False
