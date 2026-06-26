from __future__ import annotations

from src.core.binary_workbench.editor.commands.custom import (
    create_custom_command,
    safe_command_name,
)
from src.core.binary_workbench.editor.commands.models import EditorCommand

SCHEMA_VERSION = 1


def command_payload(command: EditorCommand) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "name": command.name,
        "instructions": list(command.instructions),
    }


def commands_payload(commands: dict[str, EditorCommand]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "commands": {
            name: list(command.instructions)
            for name, command in sorted(commands.items())
        },
    }


def command_from_payload(payload: dict[str, object] | None) -> EditorCommand | None:
    commands = commands_from_payload(payload)
    return commands[0] if len(commands) == 1 else None


def commands_from_payload(payload: dict[str, object] | None) -> list[EditorCommand]:
    if not isinstance(payload, dict):
        return []
    raw_commands = payload.get("commands")
    if isinstance(raw_commands, dict):
        return _commands_from_map(raw_commands)
    return _single_command(payload)


def commands_from_context(raw: dict[str, list[str]]) -> dict[str, EditorCommand]:
    commands: dict[str, EditorCommand] = {}
    for name, lines in raw.items():
        command = _command_from_name_and_lines(name, lines)
        if command is not None:
            commands[command.name] = command
    return commands


def commands_to_context(commands: dict[str, EditorCommand]) -> dict[str, list[str]]:
    return {
        name: list(command.instructions)
        for name, command in sorted(commands.items())
    }


def _commands_from_map(raw: dict[object, object]) -> list[EditorCommand]:
    commands: list[EditorCommand] = []
    for name, lines in raw.items():
        command = _command_from_name_and_lines(str(name), lines)
        if command is not None:
            commands.append(command)
    return commands


def _single_command(payload: dict[str, object]) -> list[EditorCommand]:
    command = _command_from_name_and_lines(payload.get("name"), payload.get("instructions"))
    if command is not None:
        return [command]
    return []


def _command_from_name_and_lines(name: object, raw_lines: object) -> EditorCommand | None:
    lines = _instruction_lines(raw_lines)
    if not isinstance(name, str) or not name.strip() or not lines:
        return None
    normalized = safe_command_name(name.strip().lstrip("/"))
    if not normalized:
        return None
    return EditorCommand(name=normalized, instructions=tuple(lines))


def _instruction_lines(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(line).rstrip() for line in raw]
