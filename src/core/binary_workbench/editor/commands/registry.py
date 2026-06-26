from __future__ import annotations

from src.core.binary_workbench.editor.commands.custom import custom_command_output
from src.core.binary_workbench.editor.commands.models import EditorCommand
from src.modules.contracts import CPUArchCodec


def command_names(
    custom_commands: dict[str, EditorCommand],
    architecture: CPUArchCodec | None = None,
) -> list[str]:
    system = list(architecture.editor_command_names()) if architecture is not None else []
    custom = [f"/{name}" for name in sorted(custom_commands)]
    return [*system, *custom]


def command_output(
    line: str,
    custom_commands: dict[str, EditorCommand],
    architecture: CPUArchCodec | None = None,
) -> list[str] | None:
    parsed = _parse_command(line)
    if parsed is None:
        return None
    name, args = parsed
    if architecture is not None:
        output = architecture.editor_command_output(name, args)
        if output is not None:
            return output
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
