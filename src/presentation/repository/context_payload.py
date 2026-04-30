from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.application.dto.application_state import (
    ApplicationContextDTO,
    CommandContextDTO,
    ConverterStateDTO,
    WindowSizeDTO,
)
from src.application.dto.command_entry import CommandEntryDTO


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
        key_panel_visible=payload.get("key_panel_visible", True),
        auto_convert_enabled=payload.get("auto_convert_enabled", False),
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
        "key_panel_visible": context.key_panel_visible,
        "auto_convert_enabled": context.auto_convert_enabled,
        "window_sizes": {
            key: {"width": value.width, "height": value.height}
            for key, value in context.window_sizes.items()
        },
    }


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def normalize_json_path(path: Path, directory: Path) -> Path:
    normalized = path.with_suffix(".json") if path.suffix.lower() != ".json" else path
    if not normalized.is_absolute() or directory not in normalized.parents:
        normalized = directory / normalized.name
    return normalized
