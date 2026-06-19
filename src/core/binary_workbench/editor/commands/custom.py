from __future__ import annotations

import re

from src.core.binary_workbench.editor.commands.models import EditorCommand
from src.core.binary_workbench.editor.commands.registers import replace_registers_in_lines

COMMAND_NAME = re.compile(r"[^a-zA-Z0-9_]+")
RESERVED_COMMANDS = {"sp"}


def selected_command_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.replace("\u2029", "\n").split("\n")]


def create_custom_command(
    name: str,
    lines: list[str],
) -> EditorCommand:
    return EditorCommand(name=safe_command_name(name), instructions=tuple(lines))


def safe_command_name(value: str) -> str:
    return _safe_name(value)


def custom_command_output(command: EditorCommand, args: list[str]) -> list[str]:
    return replace_registers_in_lines(list(command.instructions), args)


def _safe_name(value: str) -> str:
    name = COMMAND_NAME.sub("_", value.strip().lower()).strip("_")
    if not name:
        return ""
    return f"custom_{name}" if name in RESERVED_COMMANDS else name
