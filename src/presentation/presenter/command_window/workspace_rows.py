from __future__ import annotations

from numbers import Number

from src.application.dto.command_entry import CommandEntryDTO
from src.core.command_window.expression_inspector import ordered_assignment_names


def build_workspace_variable_detail_rows(
    instructions: list[str],
    variables: dict[str, Number],
) -> list[tuple[str, str, str]]:
    ordered_names = ordered_assignment_names(instructions, variables)
    return [
        (
            name,
            str(variables[name]),
            format_variable_hex(variables[name]),
        )
        for name in ordered_names
    ]


def build_workspace_log_rows(
    history: list[CommandEntryDTO],
) -> list[tuple[int, str, str]]:
    return [
        (index, entry.input, entry.output or "")
        for index, entry in enumerate(history)
    ]


def format_variable_hex(value: object) -> str:
    if isinstance(value, bool):
        numeric_value = int(value)
    elif isinstance(value, int):
        numeric_value = value
    elif isinstance(value, float) and value.is_integer():
        numeric_value = int(value)
    else:
        return ""

    prefix = "-" if numeric_value < 0 else ""
    return f"{prefix}0x{abs(numeric_value):X}"
