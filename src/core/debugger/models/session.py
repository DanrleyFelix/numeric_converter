from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DebuggerSessionState(str, Enum):
    """Represent the externally observable lifecycle of one debugger session."""

    READY = "Ready"
    RUNNING = "Running"
    PAUSED = "Paused"
    STOPPED = "Stopped"
    ERROR = "Error"


class DebuggerEndianness(str, Enum):
    """Describe the byte order required by an execution backend."""

    LITTLE = "little"
    BIG = "big"


class DebuggerErrorCode(str, Enum):
    """Classify failures that callers can handle without backend exceptions."""

    INVALID_STATE = "invalid_state"
    INVALID_REGISTER = "invalid_register"
    INVALID_MEMORY = "invalid_memory"
    INVALID_DIRECTIVE = "invalid_directive"
    ASSEMBLY_FAILED = "assembly_failed"
    IMPORT_FAILED = "import_failed"
    IMPORT_CYCLE = "import_cycle"
    MEMORY_COLLISION = "memory_collision"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    EXECUTION_FAILED = "execution_failed"


@dataclass(frozen=True)
class DebuggerRegister:
    """Describe one architecture register exposed to presentation code."""

    name: str
    bits: int
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class DebuggerStepRules:
    """Describe architecture-specific stepping behavior without UI knowledge."""

    instruction_size: int
    delay_slots: int = 0
    call_mnemonics: tuple[str, ...] = ()


@dataclass(frozen=True)
class DebuggerBreakpoint:
    """Represent a non-invasive execution breakpoint."""

    address: int
    enabled: bool = True
    origin: str = ""
    instruction: str = ""
    valid: bool = True
    name: str = ""

@dataclass(frozen=True)
class DebuggerInstruction:
    """Represent one assembled instruction mapped into the debug image."""

    address: int
    data: bytes
    raw_instruction: str
    origin: str
    status: str = "Ready"


@dataclass(frozen=True)
class DebuggerEvent:
    """Describe an execution event suitable for logs and observers."""

    level: str
    message: str
    address: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DebuggerStatistics:
    """Hold counters produced by execution and memory hooks."""

    executed: dict[int, int] = field(default_factory=dict)
    reads: dict[int, int] = field(default_factory=dict)
    writes: dict[int, int] = field(default_factory=dict)
    ignored: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class DebuggerMemoryRange:
    """Represent the inclusive virtual address range declared by a source."""

    start: int
    end: int
@dataclass(frozen=True)
class DebuggerImport:
    """Represent one source reference and its requested virtual address."""

    source: str
    address: int
    line: int
@dataclass(frozen=True)
class DebuggerRegisterValue:
    """Represent one initial register value declared by a source."""

    register: str
    value: int
    line: int


@dataclass(frozen=True)
class DebuggerIgnoredAddress:
    """Represent one explicitly ignored control-flow destination."""

    register: str
    address: int
    line: int


@dataclass(frozen=True)
class DebuggerDirectiveDocument:
    """Hold parsed directives and assembly lines with directives removed."""

    memory_range: DebuggerMemoryRange | None
    imports: tuple[DebuggerImport, ...]
    register_values: tuple[DebuggerRegisterValue, ...]
    ignored_addresses: tuple[DebuggerIgnoredAddress, ...]
    assembly_lines: tuple[str, ...]
    directive_lines: tuple[int, ...]


class DebuggerError(RuntimeError):
    """Expose a controlled debugger failure with structured context."""

    def __init__(
        self,
        code: DebuggerErrorCode,
        message: str,
        *,
        line: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a controlled failure for use across debugger layers."""

        super().__init__(message)
        self.code = code
        self.message = message
        self.line = line
        self.details = dict(details or {})
