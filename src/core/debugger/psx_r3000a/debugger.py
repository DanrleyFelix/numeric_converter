from __future__ import annotations

from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.models.session import (
    DebuggerEndianness,
    DebuggerStepRules,
)
from src.core.debugger.psx_r3000a.execution.session import PsxExecutionSessionMixin
from src.core.debugger.psx_r3000a.registers import PsxR3000ARegisters
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)


class BWDebuggerPSXR3000A(PsxExecutionSessionMixin, BWDebugger):
    """Implement a PSX R3000A debugger without leaking MIPS into generic APIs."""

    def __init__(self) -> None:
        """Create a ready session that can receive a transactional memory image."""

        self._registers = PsxR3000ARegisters()
        self._initialize_execution()

    @property
    def architecture(self) -> str:
        """Return the Binary Workbench PSX architecture identifier."""

        return BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME

    @property
    def endianness(self) -> DebuggerEndianness:
        """Return the PSX R3000A byte order."""

        return DebuggerEndianness.LITTLE

    @property
    def registers(self) -> PsxR3000ARegisters:
        """Return the architecture-specific register implementation."""

        return self._registers

    @property
    def step_rules(self) -> DebuggerStepRules:
        """Return fixed-width MIPS stepping and delay-slot metadata."""

        return DebuggerStepRules(4, delay_slots=1, call_mnemonics=("jal", "jalr"))

    @property
    def pc(self) -> int:
        """Read the current PSX program counter."""

        return self._registers.read(self._registers.pc_register)

    @pc.setter
    def pc(self, value: int) -> None:
        """Write the current PSX program counter."""

        self._registers.write(self._registers.pc_register, value)

