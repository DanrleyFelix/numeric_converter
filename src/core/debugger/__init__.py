"""Architecture-neutral debugger contracts and initial implementations."""

from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.contracts.registers import BWDebuggerRegs
from src.core.debugger.models.session import (
    DebuggerBreakpoint,
    DebuggerEndianness,
    DebuggerError,
    DebuggerErrorCode,
    DebuggerEvent,
    DebuggerInstruction,
    DebuggerDirectiveDocument,
    DebuggerIgnoredAddress,
    DebuggerImport,
    DebuggerMemoryRange,
    DebuggerRegister,
    DebuggerRegisterValue,
    DebuggerSessionState,
    DebuggerStatistics,
    DebuggerStepRules,
)
from src.core.debugger.psx_r3000a.debugger import BWDebuggerPSXR3000A
from src.core.debugger.directives.parser import parse_debugger_directives

__all__ = [
    "BWDebugger",
    "BWDebuggerPSXR3000A",
    "BWDebuggerRegs",
    "DebuggerBreakpoint",
    "DebuggerDirectiveDocument",
    "DebuggerEndianness",
    "DebuggerError",
    "DebuggerErrorCode",
    "DebuggerEvent",
    "DebuggerInstruction",
    "DebuggerIgnoredAddress",
    "DebuggerImport",
    "DebuggerMemoryRange",
    "DebuggerRegister",
    "DebuggerRegisterValue",
    "DebuggerSessionState",
    "DebuggerStatistics",
    "DebuggerStepRules",
    "parse_debugger_directives",
]
