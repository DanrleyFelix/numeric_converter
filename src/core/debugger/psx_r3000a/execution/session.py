from __future__ import annotations

from src.core.debugger.models.session import (
    DebuggerError,
    DebuggerErrorCode,
    DebuggerEvent,
    DebuggerSessionState,
    DebuggerStatistics,
)
from src.core.debugger.psx_r3000a.control.flow import decode_control_flow
from src.core.debugger.psx_r3000a.execution.breakpoint.session import (
    PsxExecutionBreakpointMixin,
)
from src.core.debugger.psx_r3000a.execution.running.session import PsxRunSessionMixin
from src.core.debugger.psx_r3000a.execution.state import PsxExecutionStateMixin


class PsxExecutionSessionMixin(
    PsxExecutionBreakpointMixin,
    PsxRunSessionMixin,
    PsxExecutionStateMixin,
):
    """Implement PSX inspection and step operations against Unicorn."""

    def read_memory(self, address: int, size: int) -> bytes:
        """Read bytes through the configured execution backend."""

        return self._required_backend().read_memory(address, size)

    def write_memory(self, address: int, data: bytes) -> None:
        """Write bytes to the isolated backend and record the volatile edit."""

        self._required_backend().write_memory(address, data)
        details = {"size": len(data), "value": int.from_bytes(data, "little")}
        self._events.append(
            DebuggerEvent("Memory", f"Edited memory at 0x{address:08X}.", address, details)
        )

    def step(self) -> None:
        """Execute one logical instruction and synchronize all registers."""

        if self._state not in {DebuggerSessionState.READY, DebuggerSessionState.PAUSED}:
            raise self._state_error("step")
        self._clear_breakpoint_hits()
        try:
            self._execute_current()
        except DebuggerError as error:
            self._fail(error)
            raise
        if self._finish_at_program_end():
            return
        self._state = DebuggerSessionState.PAUSED

    def restart(self) -> None:
        """Restore snapshots while preserving breakpoints and IGNORED metadata."""

        self._pause_requested = False
        self._stop_requested = True
        self._clear_breakpoint_hits()
        if self._backend is not None:
            self._backend.stop()
            self._backend.reset()
        self._registers.reset(self._image.initial_registers if self._image else {})
        self._statistics = DebuggerStatistics()
        self._events.append(DebuggerEvent("Info", "Debugger session restarted."))
        self._last_error = None
        self._stop_requested = False
        self._state = DebuggerSessionState.READY

    def _execute_current(self) -> None:
        """Execute or explicitly bypass the current instruction."""

        backend = self._required_backend()
        address = self.pc
        instruction = self._instruction_at(address)
        data = backend.read_memory(address, self.step_rules.instruction_size)
        if self._instructions and instruction is None:
            raise DebuggerError(
                DebuggerErrorCode.EXECUTION_FAILED,
                (
                    f"PC 0x{address:08X} does not point to a loaded instruction. "
                    "If this is an intentional JAL/JALR destination, mark the "
                    "call instruction as IGNORED."
                ),
            )
        if address in self._ignored_instructions:
            self._skip_as_nop(address, address, "instruction")
            return
        register_values = self._registers.snapshot()
        flow = decode_control_flow(data, address, register_values)
        ignored_addresses = self._image.ignored_addresses if self._image else frozenset()
        if flow is not None and flow.destination in ignored_addresses:
            self._skip_as_nop(address, flow.destination, flow.mnemonic)
            return
        self._prepare_breakpoint_step()
        backend.write_registers(register_values)
        backend.step()
        updated_registers = backend.read_registers()
        self._registers.reset(updated_registers)
        raw_instruction = instruction.raw_instruction if instruction else "Instruction executed"
        self._events.append(DebuggerEvent("Execution", raw_instruction, address))
        self._complete_breakpoint_step(
            address,
            register_values,
            updated_registers,
        )

    def _finish_at_program_end(self) -> bool:
        """Stop cleanly when execution advances past the final loaded instruction."""

        if self._instructions:
            final_address = max(
                instruction.address + len(instruction.data)
                for instruction in self._instructions
            )
        elif self._image is not None and self._image.zones:
            final_address = max(zone.end + 1 for zone in self._image.zones)
        else:
            return False
        if self.pc != final_address:
            return False
        self._state = DebuggerSessionState.STOPPED
        self._events.append(
            DebuggerEvent("Info", f"Execution completed at 0x{self.pc:08X}.", self.pc)
        )
        return True

    def _skip_as_nop(self, address: int, reached: int, reason: str) -> None:
        """Advance locally without sending an explicitly ignored operation."""

        _increment(self._statistics.executed, address)
        _increment(self._statistics.ignored, reached)
        self.pc = address + self.step_rules.instruction_size
        self._required_backend().write_registers(self._registers.snapshot())
        message = f"Ignored {reason} at 0x{address:08X}; reached 0x{reached:08X}."
        self._events.append(DebuggerEvent("Execution", message, address, {"reached": reached}))


def _increment(values: dict[int, int], address: int) -> None:
    """Increment one address-indexed execution counter."""

    values[address] = values.get(address, 0) + 1
