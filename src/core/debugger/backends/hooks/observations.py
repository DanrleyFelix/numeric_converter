from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Literal

from unicorn import (
    UC_HOOK_CODE,
    UC_HOOK_MEM_INVALID,
    UC_HOOK_MEM_READ,
    UC_HOOK_MEM_WRITE,
    UC_MEM_WRITE,
)


@dataclass(frozen=True)
class BackendObservation:
    """Describe one execution-engine observation without UI dependencies."""

    kind: Literal["execute", "read", "write", "invalid", "alignment"]
    address: int
    size: int = 0
    value: int = 0
    pc: int | None = None
    message: str = ""


class UnicornObservationRelay:
    """Translate Unicorn hooks into stable debugger observations."""

    def __init__(self) -> None:
        """Create a disabled relay with a zero execution counter."""

        self.observer = None
        self.execution_count = 0
        self.failure: BackendObservation | None = None
        self._pc_register_id = 0
        self._contains_interval: Callable[[int, int], bool] = lambda _address, _size: False
        self._resolve_address: Callable[[object, int], int] = lambda _engine, address: address

    def install(
        self,
        engine,
        pc_register_id: int,
        contains_interval: Callable[[int, int], bool],
        resolve_address: Callable[[object, int], int],
    ) -> None:
        """Install all supported hooks on one fresh Unicorn engine."""

        self._pc_register_id = pc_register_id
        self._contains_interval = contains_interval
        self._resolve_address = resolve_address
        engine.hook_add(UC_HOOK_CODE, self._on_code)
        engine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self._on_memory)
        engine.hook_add(UC_HOOK_MEM_INVALID, self._on_invalid_memory)

    def reset_count(self) -> None:
        """Clear the count before one execution operation."""

        self.execution_count = 0
        self.failure = None

    def publish_failure(
        self,
        kind: Literal["invalid", "alignment"],
        address: int,
        pc: int,
        message: str,
        size: int = 0,
    ) -> None:
        """Publish a failure translated from a terminal Unicorn exception."""

        self.failure = BackendObservation(kind, address, size, pc=pc, message=message)
        self._publish(self.failure)

    def _on_code(self, _engine, address: int, size: int, _data) -> None:
        """Publish instruction execution from Unicorn's code hook."""

        self.execution_count += 1
        self._publish(BackendObservation("execute", address, size, pc=address))

    def _on_memory(
        self,
        engine,
        access: int,
        address: int,
        size: int,
        value: int,
        _data,
    ) -> None:
        """Publish reads, writes and potentially unaligned accesses."""

        kind = "write" if access == UC_MEM_WRITE else "read"
        virtual_address = self._resolve_address(engine, address)
        if not self._contains(virtual_address, size):
            pc = int(engine.reg_read(self._pc_register_id)) & 0xFFFFFFFF
            message = f"Invalid memory access at 0x{virtual_address:08X}."
            self.publish_failure("invalid", virtual_address, pc, message, size)
            engine.emu_stop()
            return
        if kind == "read" and size > 0:
            value = int.from_bytes(engine.mem_read(address, size), "little")
        pc = int(engine.reg_read(self._pc_register_id)) & 0xFFFFFFFF
        self._publish(BackendObservation(kind, virtual_address, size, value, pc))
        if size in {2, 4} and virtual_address % size:
            self._publish(BackendObservation("alignment", virtual_address, size, value, pc))

    def _on_invalid_memory(
        self,
        engine,
        _access: int,
        address: int,
        size: int,
        value: int,
        _data,
    ) -> bool:
        """Report invalid memory and let Unicorn stop the current operation."""

        pc = int(engine.reg_read(self._pc_register_id)) & 0xFFFFFFFF
        virtual_address = self._resolve_address(engine, address)
        message = f"Invalid memory access at 0x{virtual_address:08X}."
        self.failure = BackendObservation("invalid", virtual_address, size, value, pc, message)
        self._publish(self.failure)
        return False

    def _publish(self, observation: BackendObservation) -> None:
        """Forward an observation when a debugger listener is configured."""

        if self.observer is not None:
            self.observer(observation)

    def _contains(self, address: int, size: int) -> bool:
        """Return whether a resolved hook interval belongs to mapped memory."""

        return self._contains_interval(address, size)
