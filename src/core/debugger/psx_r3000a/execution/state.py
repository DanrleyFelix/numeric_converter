from __future__ import annotations

from collections.abc import Sequence

from src.core.debugger.backends.unicorn_psx import UnicornPSXR3000ABackend
from src.core.debugger.breakpoints.conditions import register_aliases
from src.core.debugger.memory.image import DebuggerMemoryImage
from src.core.debugger.models.session import (
    DebuggerBreakpoint,
    DebuggerError,
    DebuggerErrorCode,
    DebuggerEvent,
    DebuggerInstruction,
    DebuggerSessionState,
    DebuggerStatistics,
)
from src.core.debugger.psx_r3000a.control.session import PsxSessionControlMixin
from src.core.debugger.psx_r3000a.execution.ranges import (
    build_executable_ranges,
    entry_executable_range,
)
from src.core.debugger.psx_r3000a.hooks.session import PsxObservationMixin


class PsxExecutionStateMixin(PsxSessionControlMixin, PsxObservationMixin):
    """Own PSX session state shared by execution operations."""

    def _initialize_execution(self) -> None:
        """Initialize an unconfigured debugger session."""

        self._state = DebuggerSessionState.READY
        self._backend: UnicornPSXR3000ABackend | None = None
        self._image: DebuggerMemoryImage | None = None
        self._breakpoints: dict[int, DebuggerBreakpoint] = {}
        self._next_breakpoint_identifier = -1
        self._pending_breakpoint_identifier: int | None = None
        self._breakpoint_hit_during_step = False
        self._register_aliases = register_aliases(self._registers.descriptors)
        self._ignored_instructions: set[int] = set()
        self._pause_requested = False
        self._stop_requested = False
        self._statistics = DebuggerStatistics()
        self._instructions: tuple[DebuggerInstruction, ...] = ()
        self._instruction_addresses: frozenset[int] = frozenset()
        self._executable_ranges = ()
        self._entry_executable_range = None
        self._last_transition = None
        self._events: list[DebuggerEvent] = []
        self._last_error: DebuggerError | None = None
        self._execution_interval_ms = 0

    def configure_memory(
        self,
        image: DebuggerMemoryImage,
        instructions: Sequence[DebuggerInstruction] = (),
    ) -> None:
        """Bind a complete image and reset the session to its initial state."""

        self._image = image
        self._backend = UnicornPSXR3000ABackend(image)
        self._backend.set_observer(self._observe_backend)
        self._registers.reset(image.initial_registers)
        self._instructions = tuple(instructions)
        self._instruction_addresses = frozenset(item.address for item in instructions)
        self._executable_ranges = build_executable_ranges(self._instructions)
        self._entry_executable_range = entry_executable_range(
            self._executable_ranges,
            image.initial_pc,
        )
        self._last_transition = None
        self._statistics = DebuggerStatistics()
        self._pause_requested = False
        self._stop_requested = False
        self._events = [
            DebuggerEvent("Info", "Debugger session opened."),
            DebuggerEvent("Info", "Virtual memory initialized."),
            DebuggerEvent(
                "Info",
                f"Virtual memory range: 0x{image.start:08X}-0x{image.end:08X}.",
            ),
            *(
                DebuggerEvent(
                    "Info",
                    f"Import loaded: {zone.origin} at 0x{zone.start:08X} "
                    f"({zone.loaded_bytes} bytes).",
                    zone.start,
                )
                for zone in image.zones
            ),
        ]
        if image.overlaps:
            overwritten = sum(item.size for item in image.overlaps)
            self._events.append(
                DebuggerEvent(
                    "Warning",
                    f"{len(image.overlaps)} import overlap(s) detected; "
                    f"later imports overwrote {overwritten} byte(s).",
                )
            )
        if image.stack_start is not None and image.stack_end is not None:
            self._events.append(
                DebuggerEvent(
                    "Info",
                    f"Stack memory mapped: 0x{image.stack_start:08X}-"
                    f"0x{image.stack_end:08X}.",
                )
            )
        self._last_error = None
        self._state = DebuggerSessionState.READY

    @property
    def state(self) -> DebuggerSessionState:
        """Return the current lifecycle state."""

        return self._state

    @property
    def breakpoints(self) -> tuple[DebuggerBreakpoint, ...]:
        """Return breakpoint metadata ordered by address."""

        return tuple(sorted(
            self._breakpoints.values(),
            key=lambda item: (item.address is None, item.address or 0, item.identifier),
        ))

    @property
    def statistics(self) -> DebuggerStatistics:
        """Return execution and memory counters."""

        return self._statistics

    @property
    def instructions(self) -> tuple[DebuggerInstruction, ...]:
        """Return all instructions loaded into the session."""

        return self._instructions

    @property
    def events(self) -> tuple[DebuggerEvent, ...]:
        """Return recorded events as an immutable sequence."""

        return tuple(self._events)

    @property
    def last_error(self) -> DebuggerError | None:
        """Return the latest controlled backend failure."""

        return self._last_error

    def _required_backend(self) -> UnicornPSXR3000ABackend:
        """Return the configured backend or raise a controlled setup error."""

        if self._backend is not None:
            return self._backend
        error = DebuggerError(
            DebuggerErrorCode.BACKEND_UNAVAILABLE,
            "The PSX R3000A execution backend is not configured.",
        )
        self._fail(error)
        raise error

    def _state_error(self, operation: str) -> DebuggerError:
        """Create an invalid-state error for one requested operation."""

        return DebuggerError(
            DebuggerErrorCode.INVALID_STATE,
            f"Cannot {operation} a debugger session in state {self._state.value}.",
        )

    def _fail(self, error: DebuggerError) -> None:
        """Retain one controlled error and expose the Error session state."""

        self._last_error = error
        self._events.append(DebuggerEvent("Error", error.message))
        self._state = DebuggerSessionState.ERROR
