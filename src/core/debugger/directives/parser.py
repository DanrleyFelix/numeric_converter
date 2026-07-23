from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence

from src.core.binary_workbench.mips_r3000a.comments import strip_comment
from src.core.debugger.directives.constants import (
    ARGUMENT_COUNTS,
    DEBUGGER_DIRECTIVE_NAMES,
    DEFINE,
    DIRECTIVE_PREFIX,
    IGNORE,
    IMPORT,
    VIRTUAL_MEMORY_RANGE,
)
from src.core.debugger.models.session import (
    DebuggerDirectiveDocument,
    DebuggerError,
    DebuggerErrorCode,
    DebuggerIgnoredAddress,
    DebuggerImport,
    DebuggerMemoryRange,
    DebuggerRegisterValue,
)

HEX_VALUE = re.compile(r"0x[0-9a-f]+", re.IGNORECASE)
REGISTER = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*|\$[0-9]+")
LABEL_ONLY = re.compile(r"[A-Za-z_.$][A-Za-z0-9_.$]*:\s*")


def parse_debugger_directives(
    lines: Sequence[str],
    symbols: Mapping[str, str] | None = None,
    *,
    main_file: bool = True,
    is_instruction: Callable[[str], bool] | None = None,
) -> DebuggerDirectiveDocument:
    """Parse debugger directives without resolving files or building memory."""

    source_lines = tuple(str(line) for line in lines)
    if main_file:
        _require_memory_range_first(source_lines)
    values = {str(key).casefold(): str(value) for key, value in (symbols or {}).items()}
    memory_range: DebuggerMemoryRange | None = None
    imports: list[DebuggerImport] = []
    register_values: list[DebuggerRegisterValue] = []
    ignored: list[DebuggerIgnoredAddress] = []
    assembly_lines = list(source_lines)
    directive_lines: list[int] = []
    instruction_found = False
    predicate = is_instruction or (lambda text: not LABEL_ONLY.fullmatch(text.strip()))
    for index, original in enumerate(source_lines):
        code = strip_comment(original).strip()
        if not code:
            continue
        if not code.startswith(DIRECTIVE_PREFIX):
            instruction_found = instruction_found or predicate(code)
            continue
        line = index + 1
        if instruction_found:
            raise _error(line, "Debugger directives must appear before assembly instructions.")
        command, arguments = _directive_parts(code, line)
        _validate_argument_count(command, arguments, line)
        if command == VIRTUAL_MEMORY_RANGE:
            if not main_file:
                raise _error(line, "virtual_memory_range is allowed only in the main file.")
            if memory_range is not None:
                raise _error(line, "Only one virtual_memory_range declaration is allowed.")
            start = _hex_value(arguments[0], values, line)
            end = _hex_value(arguments[1], values, line)
            if start >= end:
                raise _error(line, "virtual_memory_range start must be lower than its end.")
            memory_range = DebuggerMemoryRange(start, end)
        elif command == IMPORT:
            imports.append(DebuggerImport(arguments[0], _hex_value(arguments[1], values, line), line))
        elif command == DEFINE:
            register_values.append(
                DebuggerRegisterValue(
                    _register(arguments[0], line),
                    _hex_value(arguments[1], values, line),
                    line,
                )
            )
        elif command == IGNORE:
            ignored.append(
                DebuggerIgnoredAddress(
                    _register(arguments[0], line),
                    _hex_value(arguments[1], values, line),
                    line,
                )
            )
        assembly_lines[index] = ""
        directive_lines.append(index)
    return DebuggerDirectiveDocument(
        memory_range,
        tuple(imports),
        tuple(register_values),
        tuple(ignored),
        tuple(assembly_lines),
        tuple(directive_lines),
    )


def _require_memory_range_first(lines: tuple[str, ...]) -> None:
    """Require the main source to declare its virtual range on line one."""

    if not lines:
        raise _error(1, "virtual_memory_range is required on the first line.")
    command, _arguments = _directive_parts(strip_comment(lines[0]).strip(), 1)
    if command != VIRTUAL_MEMORY_RANGE:
        raise _error(1, "virtual_memory_range is required on the first line.")


def _directive_parts(code: str, line: int) -> tuple[str, list[str]]:
    """Split one complete directive into its command and arguments."""

    if not code.startswith(DIRECTIVE_PREFIX):
        return "", []
    parts = code[len(DIRECTIVE_PREFIX) :].strip().split()
    if not parts or parts[0].casefold() not in DEBUGGER_DIRECTIVE_NAMES:
        raise _error(line, "Unknown debugger directive.")
    return parts[0].casefold(), parts[1:]


def _validate_argument_count(command: str, arguments: list[str], line: int) -> None:
    """Validate the exact arity of a recognized directive."""

    expected = ARGUMENT_COUNTS[command]
    if len(arguments) != expected:
        raise _error(line, f"{command} expects exactly {expected} arguments.")


def _hex_value(token: str, symbols: Mapping[str, str], line: int) -> int:
    """Resolve a literal or Symbol that contains an exclusive hex value."""

    value = token if HEX_VALUE.fullmatch(token) else symbols.get(token.casefold(), "")
    if not HEX_VALUE.fullmatch(value):
        raise _error(line, f"{token} must be a hexadecimal literal or hexadecimal Symbol.")
    return int(value, 16)


def _register(token: str, line: int) -> str:
    """Validate and normalize a register token used by a directive."""

    if not REGISTER.fullmatch(token):
        raise _error(line, f"{token} is not a valid register name.")
    return token.casefold()


def _error(line: int, message: str) -> DebuggerError:
    """Create a line-aware controlled directive error."""

    return DebuggerError(DebuggerErrorCode.INVALID_DIRECTIVE, message, line=line)
