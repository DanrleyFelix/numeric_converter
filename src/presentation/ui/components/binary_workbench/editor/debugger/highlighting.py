from __future__ import annotations

import re

from PySide6.QtGui import QColor, QTextCharFormat

from src.core.debugger.directives.constants import (
    DEFINE,
    IGNORE,
    IMPORT,
    VIRTUAL_MEMORY_RANGE,
)
from src.core.debugger.directives.parser import HEX_VALUE
from src.presentation.ui.components.binary_workbench.editor.constants.highlighter_rules import (
    DEBUGGER_DIRECTIVE_HIGHLIGHTER,
)
from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_highlight_color,
)

DEBUGGER_DIRECTIVE_ERRORS_PROPERTY = "debuggerDirectiveErrors"
DIRECTIVE_LINE = re.compile(r"^(\s*)(\*)(\s*)([A-Za-z_][A-Za-z0-9_]*)(.*)$")
DIRECTIVE_TOKEN = re.compile(r"\S+")
SYMBOL_VALUE = re.compile(r"[A-Za-z_.$@][A-Za-z0-9_.$@]*")


def is_debugger_directive_line(text: str) -> bool:
    """Return whether a source line starts with the debugger marker."""

    return text.lstrip().startswith("*")


def highlight_debugger_directive(highlighter, text: str, error: str = "") -> None:
    """Apply debugger directive colors and optional full-line error feedback."""

    match = DIRECTIVE_LINE.match(text)
    if match is None:
        return
    star_start = len(match.group(1))
    command_start = star_start + 1 + len(match.group(3))
    command = match.group(4).casefold()
    _format(highlighter, star_start, 1, DEBUGGER_DIRECTIVE_HIGHLIGHTER["marker"])
    _format(
        highlighter,
        command_start,
        len(match.group(4)),
        DEBUGGER_DIRECTIVE_HIGHLIGHTER["command"],
    )
    arguments_start = command_start + len(match.group(4))
    arguments = [(arguments_start + item.start(), item.group()) for item in DIRECTIVE_TOKEN.finditer(match.group(5))]
    if command == IMPORT and arguments:
        _format(highlighter, arguments[0][0], len(arguments[0][1]), DEBUGGER_DIRECTIVE_HIGHLIGHTER["file"])
    value_indexes = (0, 1) if command == VIRTUAL_MEMORY_RANGE else (1,)
    for index in value_indexes:
        if index < len(arguments):
            _format(highlighter, arguments[index][0], len(arguments[index][1]), DEBUGGER_DIRECTIVE_HIGHLIGHTER["hex"])
    if command in {DEFINE, IGNORE} and arguments:
        register = arguments[0][1]
        color = psx_mips_highlight_color("registers", "$sp" if register.casefold() == "$pc" else register)
        if color is not None:
            _format(highlighter, arguments[0][0], len(register), color)
    if error and _has_value_candidate(command, arguments):
        _background(highlighter, len(text), DEBUGGER_DIRECTIVE_HIGHLIGHTER["invalid"])


def _format(highlighter, start: int, length: int, color: str, background: bool = False) -> None:
    """Apply one foreground or background span through a QSyntaxHighlighter."""

    style = QTextCharFormat()
    if background:
        style.setBackground(QColor(color))
    else:
        style.setForeground(QColor(color))
    highlighter.setFormat(start, max(1, length), style)


def _has_value_candidate(command: str, arguments: list[tuple[int, str]]) -> bool:
    """Return whether the user has entered a hexadecimal or Symbol value."""

    indexes = (0, 1) if command == VIRTUAL_MEMORY_RANGE else (1,)
    return any(
        index < len(arguments)
        and bool(HEX_VALUE.fullmatch(arguments[index][1]) or SYMBOL_VALUE.fullmatch(arguments[index][1]))
        for index in indexes
    )


def _background(highlighter, length: int, color: str) -> None:
    """Merge an error background without erasing token foreground colors."""

    for position in range(length):
        style = highlighter.format(position)
        style.setBackground(QColor(color))
        highlighter.setFormat(position, 1, style)
