from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from src.core.binary_workbench.mips_r3000a.comments import strip_comment
from src.core.debugger.directives.constants import (
    DEFINE,
    DIRECTIVE_PREFIX,
    IGNORE,
    IMPORT,
    VIRTUAL_MEMORY_RANGE,
)
from src.core.debugger.directives.parser import (
    _directive_parts,
    _hex_value,
    _register,
    _validate_argument_count,
)
from src.core.debugger.models.session import DebuggerError


def debugger_directive_diagnostics(
    lines: Sequence[str],
    symbols: Mapping[str, str] | None = None,
    is_instruction: Callable[[str], bool] | None = None,
) -> dict[int, str]:
    """Return one explanatory validation message for every invalid directive."""

    values = {str(key).casefold(): str(value) for key, value in (symbols or {}).items()}
    predicate = is_instruction or (lambda text: bool(text.strip()))
    errors: dict[int, str] = {}
    instruction_found = False
    range_line: int | None = None
    for index, original in enumerate(lines):
        code = strip_comment(str(original)).strip()
        if not code:
            continue
        if not code.startswith(DIRECTIVE_PREFIX):
            instruction_found = instruction_found or predicate(code)
            continue
        line = index + 1
        if instruction_found:
            errors[index] = "Debugger directives must appear before assembly instructions."
            continue
        try:
            command, arguments = _directive_parts(code, line)
            _validate_argument_count(command, arguments, line)
            if command == VIRTUAL_MEMORY_RANGE:
                if index != 0:
                    raise _diagnostic(line, "virtual_memory_range must be on the first line.")
                if range_line is not None:
                    raise _diagnostic(line, "Only one virtual_memory_range declaration is allowed.")
                start = _hex_value(arguments[0], values, line)
                end = _hex_value(arguments[1], values, line)
                if start >= end:
                    raise _diagnostic(
                        line,
                        "virtual_memory_range start must be lower than its end.",
                    )
                range_line = index
            elif command == IMPORT:
                _hex_value(arguments[1], values, line)
            elif command in {DEFINE, IGNORE}:
                _register(arguments[0], line)
                _hex_value(arguments[1], values, line)
        except DebuggerError as error:
            errors[index] = error.message
    return errors


def debugger_directive_symbols(
    labels: Mapping[str, str],
    variables: Mapping[str, str],
    equates: Mapping[str, str],
) -> dict[str, str]:
    """Build all accepted directive Symbol spellings from editor scopes."""

    symbols = {str(name): str(value) for name, value in labels.items()}
    for name, value in variables.items():
        normalized = str(name).lstrip("_")
        symbols[normalized] = str(value)
        symbols[f"_{normalized}"] = str(value)
    for name, value in equates.items():
        normalized = str(name).lstrip("@")
        symbols[normalized] = str(value)
        symbols[f"@{normalized}"] = str(value)
    return symbols


def _diagnostic(line: int, message: str) -> DebuggerError:
    """Create a parser-compatible error used only during full-document checks."""

    from src.core.debugger.models.session import DebuggerErrorCode

    return DebuggerError(DebuggerErrorCode.INVALID_DIRECTIVE, message, line=line)

