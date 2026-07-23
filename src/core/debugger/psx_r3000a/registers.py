from __future__ import annotations

from src.core.debugger.contracts.registers import BWDebuggerRegs
from src.core.debugger.models.session import (
    DebuggerError,
    DebuggerErrorCode,
    DebuggerRegister,
)

REGISTER_BITS = 32
GPR_NAMES = (
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra",
)
SPECIAL_NAMES = ("hi", "lo", "pc")


class PsxR3000ARegisters(BWDebuggerRegs):
    """Store PSX R3000A registers independently from an execution engine."""

    def __init__(self) -> None:
        """Create a zeroed register file with canonical MIPS aliases."""

        self._descriptors = tuple(
            DebuggerRegister(name, REGISTER_BITS, (f"r{index}", str(index)))
            for index, name in enumerate(GPR_NAMES)
        ) + tuple(DebuggerRegister(name, REGISTER_BITS) for name in SPECIAL_NAMES)
        self._aliases = self._alias_map()
        self._values = {item.name: 0 for item in self._descriptors}

    @property
    def descriptors(self) -> tuple[DebuggerRegister, ...]:
        """Return the R3000A register descriptors in hardware order."""

        return self._descriptors

    @property
    def pc_register(self) -> str:
        """Return the PSX program-counter name."""

        return "pc"

    @property
    def stack_register(self) -> str:
        """Return the conventional PSX stack register name."""

        return "sp"

    def register_size(self, name: str) -> int:
        """Return the native width of a recognized R3000A register."""

        self._canonical(name)
        return REGISTER_BITS

    def read(self, name: str) -> int:
        """Read one R3000A register by name, numeric alias or `$` alias."""

        return self._values[self._canonical(name)]

    def write(self, name: str, value: int) -> None:
        """Write a masked R3000A value while preserving the zero register."""

        canonical = self._canonical(name)
        if canonical != "zero":
            self._values[canonical] = int(value) & 0xFFFFFFFF

    def snapshot(self) -> dict[str, int]:
        """Return a detached snapshot of all canonical registers."""

        return dict(self._values)

    def reset(self, values: dict[str, int] | None = None) -> None:
        """Zero the register file and apply optional initial values."""

        self._values = {item.name: 0 for item in self._descriptors}
        for name, value in (values or {}).items():
            self.write(name, value)

    def _canonical(self, name: str) -> str:
        """Resolve one external register spelling to its canonical name."""

        key = str(name).strip().lower().lstrip("$")
        canonical = self._aliases.get(key)
        if canonical is None:
            raise DebuggerError(
                DebuggerErrorCode.INVALID_REGISTER,
                f"Unknown PSX R3000A register: {name}",
            )
        return canonical

    def _alias_map(self) -> dict[str, str]:
        """Build canonical and numeric aliases for all exposed registers."""

        aliases: dict[str, str] = {}
        for descriptor in self._descriptors:
            aliases[descriptor.name] = descriptor.name
            for alias in descriptor.aliases:
                aliases[alias] = descriptor.name
        return aliases

