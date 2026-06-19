from __future__ import annotations

from src.core.binary_workbench.editor.commands.custom import custom_command_output
from src.core.binary_workbench.editor.commands.models import EditorCommand
from src.core.binary_workbench.editor.commands.stack_pointer import stack_pointer_command

SYSTEM_COMMANDS = ("/sp",)


def command_names(custom_commands: dict[str, EditorCommand]) -> list[str]:
    custom = [f"/{name}" for name in sorted(custom_commands)]
    return [*SYSTEM_COMMANDS, *custom]


def command_output(
    line: str,
    custom_commands: dict[str, EditorCommand],
) -> list[str] | None:
    parsed = _parse_command(line)
    if parsed is None:
        return None
    name, args = parsed
    if name == "sp":
        return stack_pointer_command(args)
    command = custom_commands.get(name)
    if command is None:
        return None
    return custom_command_output(command, args)


def is_editor_command_line(line: str) -> bool:
    return _parse_command(line) is not None


def _parse_command(line: str) -> tuple[str, list[str]] | None:
    code = line.partition(";")[0].strip()
    if not code.startswith("/"):
        return None
    parts = code.split()
    if not parts or parts[0] == "/":
        return None
    return parts[0].lstrip("/").lower(), parts[1:]
