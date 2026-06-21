from __future__ import annotations

from typing import Any

from src.modules.application_dtos import ApplicationContextDTO
from src.modules.command_window_dtos import CommandContextDTO, CommandEntryDTO
from src.modules.converter_dtos import ConverterStateDTO
from src.modules.shared_dtos import WindowSizeDTO


def converter_fields(raw: dict[str, Any]) -> dict[str, str]:
    fields = {
        "decimal": "",
        "binary": "",
        "hexBE": "",
        "hexLE": "",
    }
    for key in fields:
        value = raw.get(key, "")
        fields[key] = "" if value is None else str(value)
    return fields


def window_sizes(raw: dict[str, Any]) -> dict[str, WindowSizeDTO]:
    sizes: dict[str, WindowSizeDTO] = {}
    for key, value in raw.items():
        if key == "binary_workbench_window":
            continue
        if not isinstance(value, dict):
            continue
        width = value.get("width")
        height = value.get("height")
        if not isinstance(width, int) or not isinstance(height, int):
            continue
        if width <= 0 or height <= 0:
            continue
        sizes[str(key)] = WindowSizeDTO(width=width, height=height)
    return sizes


def context_from_payload(payload: dict[str, Any]) -> ApplicationContextDTO:
    converter_raw = payload.get("converter", {})
    command_raw = payload.get("command", {})

    return ApplicationContextDTO(
        converter=ConverterStateDTO(
            from_type=converter_raw.get("from_type", "decimal"),
            fields=converter_fields(converter_raw.get("fields", {})),
            message=converter_raw.get("message"),
        ),
        command=CommandContextDTO(
            active_line=command_raw.get("active_line", ""),
            history=[
                CommandEntryDTO(
                    input=item.get("input", ""),
                    output=item.get("output"),
                )
                for item in command_raw.get("history", [])
            ],
            instructions=list(command_raw.get("instructions", [])),
            variables=dict(command_raw.get("variables", {"ANS": 0})),
        ),
        window_sizes=window_sizes(payload.get("window_sizes", {})),
    )


def context_to_payload(context: ApplicationContextDTO) -> dict[str, Any]:
    return {
        "converter": {
            "from_type": context.converter.from_type,
            "fields": converter_fields(context.converter.fields),
            "message": context.converter.message,
        },
        "command": {
            "active_line": context.command.active_line,
            "history": [
                {"input": entry.input, "output": entry.output}
                for entry in context.command.history
            ],
            "instructions": list(context.command.instructions),
            "variables": dict(context.command.variables),
        },
        "window_sizes": {
            key: {"width": value.width, "height": value.height}
            for key, value in context.window_sizes.items()
        },
    }

