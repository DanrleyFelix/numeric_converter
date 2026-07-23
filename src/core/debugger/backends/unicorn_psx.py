from __future__ import annotations

from functools import partial

from unicorn import (
    UC_ARCH_MIPS,
    UC_MODE_LITTLE_ENDIAN,
    UC_MODE_MIPS32,
    Uc,
    UcError,
)
from src.core.debugger.backends.hooks.observations import UnicornObservationRelay
from src.core.debugger.backends.errors.access import psx_memory_access_details
from src.core.debugger.backends.memory.access import psx_hook_memory_address
from src.core.debugger.backends.memory.mapping import unicorn_mapping_intervals, unicorn_memory_address
from src.core.debugger.backends.registers.mapping import REGISTER_IDS
from src.core.debugger.memory.image import DebuggerMemoryImage
from src.core.debugger.models.session import DebuggerError, DebuggerErrorCode

UNICORN_PAGE_SIZE = 0x1000


class UnicornPSXR3000ABackend:
    """Execute an isolated PSX R3000A memory image through Unicorn MIPS32."""

    def __init__(self, image: DebuggerMemoryImage) -> None:
        """Create, map and initialize a little-endian MIPS32 engine."""
        self._image = image
        self._observations = UnicornObservationRelay()
        self._engine = self._new_engine()

    @property
    def execution_count(self) -> int:
        """Return the number of code-hook callbacks in the latest operation."""
        return self._observations.execution_count

    def set_observer(self, observer) -> None:
        """Receive backend observations through one optional callable."""
        self._observations.observer = observer

    @property
    def pc(self) -> int:
        """Return the engine program counter."""
        return self.read_register("pc")

    def reset(self) -> None:
        """Recreate the engine from the immutable initial image."""
        self._engine = self._new_engine()

    def read_register(self, name: str) -> int:
        """Read one canonical R3000A register from Unicorn."""
        try:
            return int(self._engine.reg_read(REGISTER_IDS[name])) & 0xFFFFFFFF
        except (KeyError, UcError) as error:
            raise self._error(f"Unable to read register {name}: {error}") from error

    def write_register(self, name: str, value: int) -> None:
        """Write one canonical R3000A register into Unicorn."""
        try:
            self._engine.reg_write(REGISTER_IDS[name], int(value) & 0xFFFFFFFF)
        except (KeyError, UcError) as error:
            raise self._error(f"Unable to write register {name}: {error}") from error

    def read_registers(self) -> dict[str, int]:
        """Return all canonical registers from the execution engine."""
        return {name: self.read_register(name) for name in REGISTER_IDS}

    def write_registers(self, values: dict[str, int]) -> None:
        """Apply a canonical register snapshot to the execution engine."""
        for name, value in values.items():
            if name in REGISTER_IDS:
                self.write_register(name, value)

    def read_memory(self, address: int, size: int) -> bytes:
        """Read a validated interval from the isolated mapped image."""
        self._validate_interval(address, size)
        try:
            return bytes(self._engine.mem_read(unicorn_memory_address(address), size))
        except UcError as error:
            raise self._error(f"Unable to read memory at 0x{address:08X}: {error}") from error

    def write_memory(self, address: int, data: bytes) -> None:
        """Write a validated interval without touching persistent files."""
        self._validate_interval(address, len(data))
        try:
            self._engine.mem_write(unicorn_memory_address(address), bytes(data))
        except UcError as error:
            raise self._error(f"Unable to write memory at 0x{address:08X}: {error}") from error

    def step(self) -> None:
        """Execute exactly one MIPS instruction from the current PC."""
        self._emulate(1)

    def run(self, limit: int = 0) -> None:
        """Execute until a stop condition or optional instruction limit."""
        self._emulate(max(0, limit))

    def stop(self) -> None:
        """Request a prompt stop from an active Unicorn emulation call."""
        try:
            self._engine.emu_stop()
        except UcError as error:
            raise self._error(f"Unable to stop execution: {error}") from error

    def _new_engine(self) -> Uc:
        """Create a fresh engine mapped to the immutable initial snapshot."""
        try:
            engine = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
            physical_start = unicorn_memory_address(self._image.start)
            for mapped_start, mapped_size in unicorn_mapping_intervals(
                self._image.ranges,
                UNICORN_PAGE_SIZE,
            ):
                engine.mem_map(mapped_start, mapped_size)
            engine.mem_write(physical_start, self._image.initial_snapshot)
            for name, value in self._image.initial_registers.items():
                if name in REGISTER_IDS:
                    engine.reg_write(REGISTER_IDS[name], value)
            resolve_address = partial(
                psx_hook_memory_address,
                pc_register_id=REGISTER_IDS["pc"],
                register_ids=REGISTER_IDS,
            )
            self._observations.install(
                engine, REGISTER_IDS["pc"], self._image.contains, resolve_address
            )
            return engine
        except UcError as error:
            raise self._error(f"Unable to initialize Unicorn: {error}") from error

    def _emulate(self, count: int) -> None:
        """Run Unicorn and translate native errors into controlled failures."""
        pc = self.pc
        self._validate_interval(pc, 4)
        self._observations.reset_count()
        try:
            self._engine.emu_start(pc, self._image.end + 1, count=count)
            if self._observations.failure is not None:
                raise self._error(self._observations.failure.message)
        except UcError as error:
            message = str(error)
            if "unaligned" in message.casefold():
                instruction = bytes(self._engine.mem_read(unicorn_memory_address(pc), 4))
                address, size = psx_memory_access_details(instruction, self.read_registers(), pc)
                self._observations.publish_failure("alignment", address, pc, message, size)
            raise self._error(f"Execution failed at 0x{pc:08X}: {error}") from error

    def _validate_interval(self, address: int, size: int) -> None:
        """Reject accesses outside the declared debugger memory range."""
        if size < 0 or not self._image.contains(address, size):
            raise DebuggerError(
                DebuggerErrorCode.INVALID_MEMORY,
                f"Memory interval 0x{address:08X}+{size} is outside the debugger image.",
            )

    def _error(self, message: str) -> DebuggerError:
        """Create a controlled backend execution error."""

        return DebuggerError(DebuggerErrorCode.EXECUTION_FAILED, message)
